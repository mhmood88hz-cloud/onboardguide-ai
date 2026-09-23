import time
from datetime import date, timedelta
from openai import OpenAI
from sqlalchemy.orm import Session
from app.config import OPENAI_API_KEY, OPENAI_MODEL, CHAT_HISTORY_LIMIT
from app.models import User, Document, ChatMessage
from app.schemas import TaskExplanationLLMResponse

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

COMPARE_MODELS = ["gpt-4o-mini", "gpt-5-mini"]

# Manche PDFs (z.B. DOORS) haben sehr textarme Seiten, wodurch ein einzelner
# Chunk viele Seiten und damit potenziell dutzende Bilder überspannen kann.
# Deckel drauf, damit der Chat nicht mit Bildern zugemüllt wird.
MAX_IMAGES_PER_CHUNK = 2
MAX_IMAGES_TOTAL      = 4

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
        "The live data section lists every colleague visible to this user together "
        "with their current Krankmeldung/Urlaub entries (date range, status, and who "
        "is covering for them). Use it directly to answer questions such as 'wer hat "
        "am <Datum> Urlaub', 'ist <Person> heute im Haus/krank/im Urlaub', or 'wer "
        "vertritt <Person>' — compare the asked date against the listed ranges instead "
        "of saying the information is unavailable. "
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
    base = db.query(Document).filter(Document.organization_id == current_user.organization_id)
    if current_user.user_role == "Verwaltung":
        return base.all()
    categories = {"Allgemein"}
    if current_user.department:
        categories.add(current_user.department)
    if current_user.assigned_project:
        categories.add(current_user.assigned_project)
    return base.filter(Document.category.in_(categories)).all()


def _images_for_chunks(similar_chunks: list[dict], db: Session) -> dict:
    """
    Lädt für alle (document_id, page) Kombinationen der Top-Chunks die dazu
    gespeicherten DocumentImage-Zeilen, damit die Chat-Antwort den passenden
    Screenshot direkt mitliefern kann (statt nur Text-Zitate zu zeigen).
    """
    from app.models import DocumentImage

    doc_ids = {c["document_id"] for c in similar_chunks if c.get("pages")}
    if not doc_ids:
        return {}

    rows = db.query(DocumentImage).filter(
        DocumentImage.document_id.in_(doc_ids)
    ).order_by(DocumentImage.document_id, DocumentImage.page_number,
              DocumentImage.sequence).all()

    by_doc_page = {}
    for img in rows:
        by_doc_page.setdefault((img.document_id, img.page_number), []).append(img)
    return by_doc_page


def _build_rag_context(
    question: str, current_user: User, db: Session
) -> tuple[str, list[str], list[dict], list[dict]]:
    from app.services.chunking_service import search_similar_chunks

    allowed_docs    = _get_allowed_docs(current_user, db)
    allowed_doc_ids = [d.id for d in allowed_docs]
    doc_id_to_title = {d.id: d.title for d in allowed_docs}

    if not allowed_doc_ids:
        return "No documents found.", [], [], []

    similar_chunks = search_similar_chunks(question, db, allowed_doc_ids)
    by_doc_page    = _images_for_chunks(similar_chunks, db)

    context_text   = ""
    context_titles = []
    chunk_stats    = []
    seen_image_ids = set()
    all_images     = []

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

            chunk_images = []
            for page in chunk.get("pages", []):
                if len(chunk_images) >= MAX_IMAGES_PER_CHUNK:
                    break
                for img in by_doc_page.get((chunk["document_id"], page), []):
                    if len(chunk_images) >= MAX_IMAGES_PER_CHUNK:
                        break
                    entry = {
                        "id":       img.id,
                        "document": doc_title,
                        "page":     img.page_number,
                        "title":    f"Abbildung {img.sequence + 1}",
                        "url":      f"/api/documents/{img.document_id}/images/{img.id}",
                    }
                    chunk_images.append(entry)
                    if img.id not in seen_image_ids and len(all_images) < MAX_IMAGES_TOTAL:
                        seen_image_ids.add(img.id)
                        all_images.append(entry)

            chunk_stats.append({
                "document":         doc_title,
                "chunk_index":      chunk["chunk_index"],
                "similarity_score": chunk["similarity_score"],
                "token_count":      chunk["token_count"],
                "images":           chunk_images,
            })
    else:
        context_text = "No relevant chunks found."

    return context_text, context_titles, chunk_stats, all_images


# ── LIVE CONTEXT ──────────────────────────────────────────────────────────
def _format_absence_lines(member: User, db: Session) -> str:
    """
    Krankmeldungen/Urlaub (genehmigt oder ausstehend) eines Mitarbeiters,
    die aktuell relevant sind – damit Fragen wie 'wer hat am 02.09 Urlaub'
    oder 'ist X heute im Haus' aus dem Chat heraus beantwortbar sind.
    Der Grund (reason) wird bewusst NICHT mitgegeben – nicht jeder, der die
    Abwesenheit sehen darf, soll auch den (ggf. medizinischen) Grund lesen.
    """
    from app.models import LeaveRequest

    cutoff = date.today() - timedelta(days=3)
    rows = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.user_id == member.id,
            LeaveRequest.status.in_(["Genehmigt", "Ausstehend"]),
            LeaveRequest.end_date >= cutoff,
        )
        .order_by(LeaveRequest.start_date)
        .all()
    )
    lines = ""
    for r in rows:
        span  = f"{r.start_date.strftime('%d.%m.%Y')} – {r.end_date.strftime('%d.%m.%Y')}"
        extra = ""
        if r.status == "Genehmigt" and r.substitute_user_id:
            sub = db.query(User).filter(User.id == r.substitute_user_id).first()
            if sub:
                extra = f", Vertretung: {sub.username}"
        lines += f"    · {r.leave_type}: {span} ({r.status}{extra})\n"
    return lines


def _format_member_block(member: User, db: Session) -> str:
    """Eine Zeile pro Mitarbeiter mit Rolle, Fortschritt und den konkreten
    offenen Aufgaben (nicht nur der Anzahl), damit gezielte Fragen wie
    'welche Aufgabe hat lisa_schmidt' beantwortbar sind."""
    from app.models import Task

    open_tasks = db.query(Task).filter(
        Task.assigned_to == member.id,
        Task.is_completed == False
    ).all()

    joined = member.created_at.strftime("%d.%m.%Y") if member.created_at else "unbekannt"

    line = (
        f"- {member.username} (Rolle: {member.user_role}, "
        f"Abteilung: {member.department or 'Allgemein'}, "
        f"hinzugefügt am: {joined}): "
        f"{member.progress_percent}% abgeschlossen, "
        f"{len(open_tasks)} offene Aufgabe(n)"
    )
    if open_tasks:
        titles = ", ".join(f"'{t.title}' ({t.task_type})" for t in open_tasks)
        line += f" – {titles}"
    line += "\n"
    line += _format_absence_lines(member, db)
    return line


def _build_live_context(current_user: User, db: Session) -> str:
    """
    Lädt Live-Daten aus der DB:
    - Eigene offene Aufgaben
    - Team-Details (Leader: direkt unterstellte Mitarbeiter mit ihren Aufgaben)
    - Firmenweite Übersicht (Verwaltung: alle Mitarbeiter mit ihren Aufgaben)
    Diese Daten verlassen das System nicht – kein Internet.
    """
    from app.models import Task

    context = f"\n=== LIVE DATEN (aus Datenbank, heutiges Datum: {date.today().strftime('%d.%m.%Y')}) ===\n"

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

    # Eigene Krankmeldungen/Urlaub – für alle Rollen
    own_absences = _format_absence_lines(current_user, db)
    context += f"\nAbwesenheiten von {current_user.username} (Krankmeldung/Urlaub):\n"
    context += own_absences if own_absences else "    · aktuell keine gemeldet\n"

    # Mitarbeiter: eigener Lead + Kollegen mit Anwesenheits-/Abwesenheitsstatus,
    # damit Fragen wie 'ist mein Lead heute im Haus' oder 'ist <Kollege> krank'
    # aus dem Chat heraus beantwortbar sind.
    if current_user.user_role == "Mitarbeiter":
        if current_user.reports_to:
            leader = db.query(User).filter(User.id == current_user.reports_to).first()
            peers  = db.query(User).filter(
                User.reports_to == current_user.reports_to,
                User.id != current_user.id,
            ).all()
            context += "\nDein Team (Anwesenheit/Abwesenheit):\n"
            if leader:
                context += f"- {leader.username} (dein Lead)\n"
                lines = _format_absence_lines(leader, db)
                context += lines if lines else "    · aktuell keine Abwesenheit gemeldet\n"
            for p in peers:
                context += f"- {p.username} (Kollege/in, Abteilung: {p.department or 'Allgemein'})\n"
                lines = _format_absence_lines(p, db)
                context += lines if lines else "    · aktuell keine Abwesenheit gemeldet\n"
        else:
            context += "\nDu bist aktuell keinem Leader/Team zugeordnet.\n"

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
        all_users = db.query(User).filter(
            User.organization_id == current_user.organization_id
        ).all()
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
) -> tuple[str, list[str], list[dict], list[dict]]:
    """Alle drei Säulen + Live Context."""
    openai_client = get_client()

    system_prompt                       = build_system_prompt(current_user)
    history                             = build_conversation_history(current_user, db)
    context_text, titles, stats, images = _build_rag_context(question, current_user, db)
    live_context                        = _build_live_context(current_user, db)

    messages = _build_messages(
        system_prompt, history, context_text, question, live_context
    )

    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=SUPPORTED_TEMPERATURE.get(OPENAI_MODEL, 0.4)
    )

    return response.choices[0].message.content, titles, stats, images


def run_model_comparison(
    current_user: User, question: str, db: Session
) -> tuple[str, list[str], list[dict], list[dict], list[dict]]:
    """Vergleicht gpt-4o-mini vs gpt-5-mini mit gleichen RAG-Daten."""
    openai_client = get_client()

    system_prompt                       = build_system_prompt(current_user)
    history                             = build_conversation_history(current_user, db)
    context_text, titles, stats, images = _build_rag_context(question, current_user, db)
    live_context                        = _build_live_context(current_user, db)

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

    return comparison_results[0]["ai_response"], titles, stats, comparison_results, images


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