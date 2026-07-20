from openai import OpenAI
from sqlalchemy.orm import Session
from app.config import OPENAI_API_KEY, OPENAI_MODEL, CHAT_HISTORY_LIMIT
from app.models import User, Document, ChatMessage
from app.schemas import TaskExplanationLLMResponse

# Initialize OpenAI client – None if no API key is configured
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def get_client():
    """Returns the OpenAI client or raises 503 if not configured."""
    from fastapi import HTTPException
    if not client:
        raise HTTPException(
            status_code=503,
            detail="OpenAI client is not active. Set OPENAI_API_KEY in .env."
        )
    return client


def build_rag_context(current_user, db) -> tuple[str, list[str], list[dict]]:
    """
    Pillar C – RAG mit Vektorsuche:
    1. Erlaubte Dokumente nach Rolle filtern
    2. Frage als Embedding → pgvector Ähnlichkeitssuche
    3. Nur top-3 relevanteste Chunks zurückgeben

    Returns:
        context_text:   Text der ans Modell geht
        context_titles: Dokumenttitel als Quellennachweis
        chunk_stats:    Similarity Scores für den Simulator
    """
    from app.models import Document
    from app.services.chunking_service import search_similar_chunks

    # Erlaubte Kategorien nach Rolle
    categories = {"Allgemein"}
    if current_user.department:
        categories.add(current_user.department)
    if current_user.assigned_project:
        categories.add(current_user.assigned_project)

    # Erlaubte Dokument-IDs laden
    allowed_docs = db.query(Document).filter(
        Document.category.in_(categories)
    ).all()
    allowed_doc_ids = [d.id for d in allowed_docs]

    if not allowed_doc_ids:
        return "No documents found.", [], []

    # Dummy-Kontext zurückgeben – echte Suche passiert in run_rag_chat
    # allowed_doc_ids wird weitergegeben
    return "", [], allowed_doc_ids


def build_conversation_history(current_user: User, db: Session) -> list[dict]:
    """
    Pillar A – Conversation History: loads the last k messages from the database
    and returns them as a list of user/assistant message dicts in chronological order.
    """
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(CHAT_HISTORY_LIMIT)
        .all()
    )
    messages = []
    for msg in reversed(history):  # reverse so oldest message comes first
        messages.append({"role": "user",      "content": msg.user_question})
        messages.append({"role": "assistant",  "content": msg.ai_response})
    return messages


def build_system_prompt(current_user: User) -> str:
    """
    Pillar B – Dynamic Context Injection: builds a personalized system prompt
    using the user's profile data from the database.
    """
    return (
        f"You are the personal onboarding assistant for {current_user.username}. "
        f"Department: '{current_user.department or 'General'}', "
        f"Project: '{current_user.assigned_project or 'None'}', "
        f"Role: '{current_user.user_role}'. "
        "Answer EXCLUSIVELY based on the provided company documents. "
        "If the answer is not in the documents, say so honestly."
    )


def run_rag_chat(current_user, question: str, db) -> tuple[str, list[str], list[dict]]:
    """
    Kombiniert alle drei Säulen + echte Vektorsuche:
    - Pillar A: Conversation History
    - Pillar B: Dynamic Context Injection
    - Pillar C: RAG mit pgvector (neu)

    Returns:
        ai_reply:       Antwort des Modells
        context_titles: genutzte Dokumenttitel
        chunk_stats:    Similarity Scores für Simulator
    """
    from app.models import Document
    from app.services.chunking_service import search_similar_chunks

    openai_client = get_client()

    # ── Pillar B: System Prompt ───────────────────────────────────────
    system_prompt = build_system_prompt(current_user)

    # ── Pillar C: Vektorsuche ─────────────────────────────────────────
    # Verwaltung sieht alle Dokumente
    if current_user.user_role == "Verwaltung":
        allowed_docs = db.query(Document).all()
    else:
        categories = {"Allgemein"}
        if current_user.department:
            categories.add(current_user.department)
        if current_user.assigned_project:
            categories.add(current_user.assigned_project)
        allowed_docs = db.query(Document).filter(
            Document.category.in_(categories)
        ).all()
    allowed_doc_ids = [d.id for d in allowed_docs]
    doc_id_to_title = {d.id: d.title for d in allowed_docs}

    # Vektorsuche – findet die relevantesten Chunks
    similar_chunks = search_similar_chunks(question, db, allowed_doc_ids)

    # Kontext aus Chunks aufbauen
    context_text   = ""
    context_titles = []
    chunk_stats    = []

    if similar_chunks:
        context_text = "=== RELEVANT DOCUMENT CHUNKS (sorted by relevance) ===\n\n"
        for chunk in similar_chunks:
            doc_title = doc_id_to_title.get(chunk["document_id"], "Unknown")
            if doc_title not in context_titles:
                context_titles.append(doc_title)
            context_text += (
                f"--- {doc_title} "
                f"(Chunk {chunk['chunk_index']}, "
                f"Similarity: {chunk['similarity_score']}) ---\n"
                f"{chunk['content']}\n\n"
            )
            chunk_stats.append({
                "document":        doc_title,
                "chunk_index":     chunk["chunk_index"],
                "similarity_score": chunk["similarity_score"],
                "token_count":     chunk["token_count"],
            })
    else:
        context_text = "No relevant chunks found for this question."

    # ── Pillar A: Conversation History ────────────────────────────────
    history  = build_conversation_history(current_user, db)

    # ── Zusammenbauen ─────────────────────────────────────────────────
    messages = [{"role": "system", "content": system_prompt}]
    messages += history
    messages.append({
        "role":    "user",
        "content": f"{context_text}\n\nQuestion: {question}"
    })

    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.4
    )

    return response.choices[0].message.content, context_titles, chunk_stats


def run_task_explanation(current_user: User, task, db: Session) -> TaskExplanationLLMResponse:
    """
    Generates a structured, personalized task explanation using OpenAI Structured Outputs.
    The model is forced to return valid JSON matching TaskExplanationLLMResponse.
    """
    openai_client = get_client()

    system_prompt = (
        "You are an experienced technical onboarding coach. "
        f"Explain the following task step by step to '{current_user.username}' "
        f"(Role: {current_user.user_role}, "
        f"Department: {current_user.department or 'General'}, "
        f"Project: {current_user.assigned_project or 'None'}). "
        "Adjust terminology, depth and examples to their profile. "
        "Respond ONLY in the specified JSON format."
    )

    prompt_content = (
        f"Task: {task.title}\n"
        f"Description: {task.description or 'No description provided'}\n"
        f"Type: {task.task_type}\n"
        f"Project: {task.project_name or 'None'}"
    )

    response = openai_client.beta.chat.completions.parse(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": prompt_content}
        ],
        response_format=TaskExplanationLLMResponse,
        temperature=0.4
    )
    return response.choices[0].message.parsed