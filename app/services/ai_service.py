import time
from openai import OpenAI
from sqlalchemy.orm import Session
from app.config import OPENAI_API_KEY, OPENAI_MODEL, CHAT_HISTORY_LIMIT
from app.models import User, Document, ChatMessage
from app.schemas import TaskExplanationLLMResponse

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

COMPARE_MODELS = ["gpt-4o-mini", "gpt-5-mini"]

COST_MAP = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
    "gpt-5-mini":  {"input": 0.00040, "output": 0.00160},
}

SUPPORTED_TEMPERATURE = {
    "gpt-4o-mini": 0.4,
    "gpt-5-mini":  1,  # gpt-5-mini only accepts the default temperature (1)
}


def get_client():
    from fastapi import HTTPException
    if not client:
        raise HTTPException(status_code=503, detail="OpenAI not configured.")
    return client


# ── PILLAR B ──────────────────────────────────────────────────────────────
def build_system_prompt(current_user: User) -> str:
    return (
        f"You are the personal onboarding assistant for {current_user.username}. "
        f"Department: '{current_user.department or 'General'}', "
        f"Project: '{current_user.assigned_project or 'None'}', "
        f"Role: '{current_user.user_role}'. "
        "Answer based on the provided company documents and live data. "
        "If the answer is not available, say so honestly."
    )


# ── PILLAR A ──────────────────────────────────────────────────────────────
def build_conversation_history(current_user: User, db: Session) -> list[dict]:
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(CHAT_HISTORY_LIMIT)
        .all()
    )
    messages = []
    for msg in reversed(history):
        messages.append({"role": "user",      "content": msg.user_question})
        messages.append({"role": "assistant",  "content": msg.ai_response})
    return messages


# ── PILLAR C ──────────────────────────────────────────────────────────────
def _get_allowed_docs(current_user: User, db: Session):
    if current_user.user_role == "Verwaltung":
        return db.query(Document).all()
    categories = {"Allgemein"}
    if current_user.department:
        categories.add(current_user.department)
    if current_user.assigned_project:
        categories.add(current_user.assigned_project)
    return db.query(Document).filter(Document.category.in_(categories)).all()


def _build_rag_context(
    question: str, current_user: User, db: Session
) -> tuple[str, list[str], list[dict]]:
    from app.services.chunking_service import search_similar_chunks

    allowed_docs    = _get_allowed_docs(current_user, db)
    allowed_doc_ids = [d.id for d in allowed_docs]
    doc_id_to_title = {d.id: d.title for d in allowed_docs}

    if not allowed_doc_ids:
        return "No documents found.", [], []

    similar_chunks = search_similar_chunks(question, db, allowed_doc_ids)

    context_text   = ""
    context_titles = []
    chunk_stats    = []

    if similar_chunks:
        context_text = "=== RELEVANT DOCUMENT CHUNKS ===\n\n"
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
                "document":         doc_title,
                "chunk_index":      chunk["chunk_index"],
                "similarity_score": chunk["similarity_score"],
                "token_count":      chunk["token_count"],
            })
    else:
        context_text = "No relevant chunks found."

    return context_text, context_titles, chunk_stats


# ── LIVE CONTEXT ──────────────────────────────────────────────────────────
def _format_member_block(member: User, db: Session) -> str:
    """Eine Zeile pro Mitarbeiter mit Rolle, Fortschritt und den konkreten
    offenen Aufgaben (nicht nur der Anzahl), damit gezielte Fragen wie
    'welche Aufgabe hat lisa_schmidt' beantwortbar sind."""
    from app.models import Task

    open_tasks = db.query(Task).filter(
        Task.assigned_to == member.id,
        Task.is_completed == False
    ).all()

    line = (
        f"- {member.username} (Rolle: {member.user_role}, "
        f"Abteilung: {member.department or 'Allgemein'}): "
        f"{member.progress_percent}% abgeschlossen, "
        f"{len(open_tasks)} offene Aufgabe(n)"
    )
    if open_tasks:
        titles = ", ".join(f"'{t.title}' ({t.task_type})" for t in open_tasks)
        line += f" – {titles}"
    return line + "\n"


def _build_live_context(current_user: User, db: Session) -> str:
    """
    Lädt Live-Daten aus der DB:
    - Eigene offene Aufgaben
    - Team-Details (Leader: direkt unterstellte Mitarbeiter mit ihren Aufgaben)
    - Firmenweite Übersicht (Verwaltung: alle Mitarbeiter mit ihren Aufgaben)
    Diese Daten verlassen das System nicht – kein Internet.
    """
    from app.models import Task

    context = "\n=== LIVE DATEN (aus Datenbank) ===\n"

    # Eigene offene Aufgaben
    open_tasks = db.query(Task).filter(
        Task.assigned_to == current_user.id,
        Task.is_completed == False
    ).all()

    if open_tasks:
        context += f"\nOffene Aufgaben von {current_user.username}:\n"
        for t in open_tasks:
            context += f"- {t.title} (Typ: {t.task_type})\n"
    else:
        context += f"\n{current_user.username} hat keine offenen Aufgaben.\n"

    # Team-Details nur für Leader: direkt unterstellte Mitarbeiter
    if current_user.user_role == "Leader":
        team = db.query(User).filter(
            User.reports_to == current_user.id
        ).all()
        if team:
            context += f"\nTeam von {current_user.username} ({len(team)} Mitarbeiter):\n"
            for member in team:
                context += _format_member_block(member, db)

    # Firmenweite Übersicht nur für Verwaltung: alle Mitarbeiter der Firma
    if current_user.user_role == "Verwaltung":
        all_users = db.query(User).all()
        context += f"\nMitarbeiter in der Firma (gesamt: {len(all_users)}):\n"
        for member in all_users:
            if member.id == current_user.id:
                continue
            context += _format_member_block(member, db)

    return context


def _build_messages(
    system_prompt: str, history: list[dict],
    context_text: str, question: str,
    live_context: str = ""
) -> list[dict]:
    messages = [{"role": "system", "content": system_prompt}]
    messages += history
    messages.append({
        "role":    "user",
        "content": f"{live_context}\n{context_text}\n\nQuestion: {question}"
    })
    return messages


# ── MAIN FUNCTIONS ────────────────────────────────────────────────────────
def run_rag_chat(
    current_user: User, question: str, db: Session
) -> tuple[str, list[str], list[dict]]:
    """Alle drei Säulen + Live Context."""
    openai_client = get_client()

    system_prompt                = build_system_prompt(current_user)
    history                      = build_conversation_history(current_user, db)
    context_text, titles, stats  = _build_rag_context(question, current_user, db)
    live_context                 = _build_live_context(current_user, db)

    messages = _build_messages(
        system_prompt, history, context_text, question, live_context
    )

    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=SUPPORTED_TEMPERATURE.get(OPENAI_MODEL, 0.4)
    )

    return response.choices[0].message.content, titles, stats


def run_model_comparison(
    current_user: User, question: str, db: Session
) -> tuple[str, list[str], list[dict], list[dict]]:
    """Vergleicht gpt-4o-mini vs gpt-5-mini mit gleichen RAG-Daten."""
    openai_client = get_client()

    system_prompt                = build_system_prompt(current_user)
    history                      = build_conversation_history(current_user, db)
    context_text, titles, stats  = _build_rag_context(question, current_user, db)
    live_context                 = _build_live_context(current_user, db)

    messages = _build_messages(
        system_prompt, history, context_text, question, live_context
    )

    comparison_results = []

    for model in COMPARE_MODELS:
        t_start  = time.time()
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=SUPPORTED_TEMPERATURE.get(model, 0.4)
        )
        elapsed       = round(time.time() - t_start, 2)
        input_tokens  = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        ai_reply      = response.choices[0].message.content

        rates = COST_MAP.get(model, {"input": 0, "output": 0})
        cost  = round(
            (input_tokens  / 1000 * rates["input"]) +
            (output_tokens / 1000 * rates["output"]),
            6
        )

        comparison_results.append({
            "model":         model,
            "response_time": elapsed,
            "tokens_used":   input_tokens + output_tokens,
            "cost_usd":      cost,
            "answer_length": len(ai_reply),
            "ai_response":   ai_reply,
        })

    return comparison_results[0]["ai_response"], titles, stats, comparison_results


def run_task_explanation(
    current_user: User, task, db: Session
) -> TaskExplanationLLMResponse:
    """Structured Outputs für Task-Erklärung."""
    openai_client = get_client()

    system_prompt = (
        f"You are an experienced onboarding coach. "
        f"Explain the task to '{current_user.username}' "
        f"(Role: {current_user.user_role}, "
        f"Department: {current_user.department or 'General'}). "
        "Respond ONLY in the specified JSON format."
    )

    prompt_content = (
        f"Task: {task.title}\n"
        f"Description: {task.description or 'No description'}\n"
        f"Type: {task.task_type}"
    )

    response = openai_client.beta.chat.completions.parse(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": prompt_content}
        ],
        response_format=TaskExplanationLLMResponse,
        temperature=SUPPORTED_TEMPERATURE.get(OPENAI_MODEL, 0.4)
    )
    return response.choices[0].message.parsed