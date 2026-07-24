import time
from openai import OpenAI
from sqlalchemy.orm import Session
from app.config import OPENAI_API_KEY, OPENAI_MODEL, CHAT_HISTORY_LIMIT
from app.models import User, Document, ChatMessage
from app.schemas import TaskExplanationLLMResponse

# Initialize OpenAI client – None if no API key is configured
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Models available in this project
COMPARE_MODELS = ["gpt-4o-mini", "gpt-5-mini"]

# Cost per 1K tokens (as of 2025)
COST_MAP = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
    "gpt-5-mini":  {"input": 0.00040, "output": 0.00160},
}

# gpt-5-mini only supports temperature=1
SUPPORTED_TEMPERATURE = {
    "gpt-4o-mini": 0.4,
    "gpt-5-mini":  1,
}


def get_client():
    """Returns the OpenAI client or raises 503 if not configured."""
    from fastapi import HTTPException
    if not client:
        raise HTTPException(
            status_code=503,
            detail="OpenAI client is not active. Set OPENAI_API_KEY in .env."
        )
    return client


# ── PILLAR B ──────────────────────────────────────────────────────────────────
def build_system_prompt(current_user: User) -> str:
    """
    Pillar B – Dynamic Context Injection:
    Builds a personalized system prompt using the user's profile from DB.
    """
    return (
        f"You are the personal onboarding assistant for {current_user.username}. "
        f"Department: '{current_user.department or 'General'}', "
        f"Project: '{current_user.assigned_project or 'None'}', "
        f"Role: '{current_user.user_role}'. "
        "Answer EXCLUSIVELY based on the provided company documents. "
        "If the answer is not in the documents, say so honestly."
    )


# ── PILLAR A ──────────────────────────────────────────────────────────────────
def build_conversation_history(current_user: User, db: Session) -> list[dict]:
    """
    Pillar A – Conversation History:
    Loads last k messages and returns them in chronological order.
    """
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


# ── PILLAR C ──────────────────────────────────────────────────────────────────
def _get_allowed_docs(current_user: User, db: Session):
    """
    Returns allowed documents based on user role:
    - Verwaltung → all documents
    - Others     → Allgemein + own department + own project
    """
    if current_user.user_role == "Verwaltung":
        return db.query(Document).all()

    categories = {"Allgemein"}
    if current_user.user_role == "Leader":
        for member in db.query(User).filter(User.reports_to == current_user.id).all():
            if member.department:
                categories.add(member.department)
            if member.assigned_project:
                categories.add(member.assigned_project)
    else:
        if current_user.department:
            categories.add(current_user.department)
        if current_user.assigned_project:
            categories.add(current_user.assigned_project)
    return db.query(Document).filter(Document.category.in_(categories)).all()


def _build_rag_context(
    question: str,
    current_user: User,
    db: Session
) -> tuple[str, list[str], list[dict]]:
    """
    Pillar C – RAG with vector search:
    1. Filter allowed documents by role
    2. Convert question to embedding → pgvector cosine search
    3. Return top-k most relevant chunks with similarity scores
    """
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
                "document":         doc_title,
                "chunk_index":      chunk["chunk_index"],
                "similarity_score": chunk["similarity_score"],
                "token_count":      chunk["token_count"],
            })
    else:
        context_text = "No relevant chunks found for this question."

    return context_text, context_titles, chunk_stats


def _build_messages(
    system_prompt: str,
    history: list[dict],
    context_text: str,
    question: str
) -> list[dict]:
    """Assembles the full message payload for OpenAI."""
    messages = [{"role": "system", "content": system_prompt}]
    messages += history
    messages.append({
        "role":    "user",
        "content": f"{context_text}\n\nQuestion: {question}"
    })
    return messages


# ── MAIN FUNCTIONS ────────────────────────────────────────────────────────────
def run_rag_chat(
    current_user: User, question: str, db: Session
) -> tuple[str, list[str], list[dict]]:
    """
    Combines all three pillars and runs OpenAI chat completion.

    Returns:
        ai_reply:       model answer
        context_titles: document titles used as sources
        chunk_stats:    similarity scores for the simulator
    """
    openai_client = get_client()

    system_prompt              = build_system_prompt(current_user)
    context_text, titles, stats = _build_rag_context(question, current_user, db)
    history                    = build_conversation_history(current_user, db)
    messages                   = _build_messages(system_prompt, history,
                                                 context_text, question)

    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=SUPPORTED_TEMPERATURE.get(OPENAI_MODEL, 0.4)
    )

    return response.choices[0].message.content, titles, stats


def run_model_comparison(
    current_user: User, question: str, db: Session
) -> tuple[str, list[str], list[dict], list[dict]]:
    """
    Runs the same RAG question through gpt-4o-mini AND gpt-5-mini.
    Measures and compares: response time, tokens, cost, answer length.

    The RAG context (chunks + embeddings) is built ONCE and reused for both
    models – this ensures a fair comparison since retrieval is model-independent.

    Returns:
        main_reply:   answer from first model (gpt-4o-mini)
        titles:       document titles used
        chunk_stats:  similarity scores
        comparison:   list of stats per model
    """
    openai_client = get_client()

    # Build context once – same for both models
    system_prompt              = build_system_prompt(current_user)
    context_text, titles, stats = _build_rag_context(question, current_user, db)
    history                    = build_conversation_history(current_user, db)
    messages                   = _build_messages(system_prompt, history,
                                                 context_text, question)

    comparison_results = []

    for model in COMPARE_MODELS:
        t_start  = time.time()

        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=SUPPORTED_TEMPERATURE.get(model, 0.4)  # gpt-5-mini → 1
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

    # Return gpt-4o-mini answer as main response
    return comparison_results[0]["ai_response"], titles, stats, comparison_results


def run_task_explanation(
    current_user: User, task, db: Session
) -> TaskExplanationLLMResponse:
    """
    Generates a structured task explanation using OpenAI Structured Outputs.
    Forces the model to return exact JSON: summary + steps + tools_and_tips.
    """
    openai_client = get_client()

    system_prompt = (
        "You are an experienced technical onboarding coach. "
        f"Explain the following task step by step to '{current_user.username}' "
        f"(Role: {current_user.user_role}, "
        f"Department: {current_user.department or 'General'}, "
        f"Project: {current_user.assigned_project or 'None'}). "
        "Adjust terminology and examples to their profile. "
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
        temperature=SUPPORTED_TEMPERATURE.get(OPENAI_MODEL, 0.4)
    )
    return response.choices[0].message.parsed
