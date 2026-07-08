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


def build_rag_context(current_user: User, db: Session) -> tuple[str, list[str]]:
    """
    Pillar C – RAG: filters documents by the user's allowed categories
    and returns their text content as context string plus a list of titles.

    Filter formula:
    D_relevant = { d | d.category in {'Allgemein', user.department, user.project} }
    """
    categories = {"Allgemein"}
    if current_user.department:
        categories.add(current_user.department)
    if current_user.assigned_project:
        categories.add(current_user.assigned_project)

    documents      = db.query(Document).filter(Document.category.in_(categories)).all()
    context_text   = ""
    context_titles = []

    if documents:
        context_text = "=== COMPANY DOCUMENTS (sole source of truth) ===\n\n"
        for doc in documents:
            context_titles.append(doc.title)
            if doc.content:
                preview       = doc.content[:2000]
                context_text += f"--- {doc.title} (Category: {doc.category}) ---\n{preview}\n\n"
            else:
                context_text += f"--- {doc.title} (Category: {doc.category}) ---\n[Content not extractable]\n\n"
    else:
        context_text = "No company documents found for your profile. Answer in general terms."

    return context_text, context_titles


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


def run_rag_chat(current_user: User, question: str, db: Session) -> tuple[str, list[str]]:
    """
    Combines all three pillars and runs the OpenAI chat completion.
    Returns the AI reply and the list of document titles used as sources.
    """
    openai_client  = get_client()
    system_prompt  = build_system_prompt(current_user)
    context_text, context_titles = build_rag_context(current_user, db)
    history        = build_conversation_history(current_user, db)

    messages_payload = [{"role": "system", "content": system_prompt}]
    messages_payload += history
    messages_payload.append({
        "role":    "user",
        "content": f"{context_text}\n\nQuestion: {question}"
    })

    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages_payload,
        temperature=0.4
    )
    return response.choices[0].message.content, context_titles


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