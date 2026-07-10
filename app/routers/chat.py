import json
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ChatMessage, Task
from app.schemas import ChatRequest, ChatResponse, TaskExplainEndpointResponse
from app.security import get_current_user, load_current_user
from app.services.ai_service import run_rag_chat, run_task_explanation
from app.services.trace import start_trace, log_step, get_trace
from app.services.ws_manager import manager

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/ask", response_model=ChatResponse)
async def ask_onboarding_guide(
    request:  ChatRequest,
    response: Response,
    db:       Session = Depends(get_db),
    user_id:  int     = Depends(get_current_user)
):
    """RAG Chatbot – all three prompt engineering pillars."""
    start_trace()
    log_step("User", "Main",
             "POST /api/chat/ask",
             f"Mitarbeiter stellt eine Frage: '{request.question[:60]}...' mit x-user-id Header.")
    log_step("Main", "Security",
             "get_current_user()",
             "x-user-id Header wird extrahiert. Nur int zurück – keine eigene DB-Session.")
    log_step("Security", "Router",
             "Routing zu chat.py",
             "load_current_user() lädt User-Objekt mit bestehender Session.")

    current_user = load_current_user(user_id, db)

    log_step("Router", "AIService",
             "run_rag_chat() gestartet",
             f"ai_service.py übernimmt für User '{current_user.username}' "
             f"(Rolle: {current_user.user_role}, Abteilung: {current_user.department or 'Allgemein'}).")

    log_step("AIService", "PostgreSQL",
             "Säule C: RAG-Dokumente laden",
             f"Filtert Dokumente nach Kategorie: Allgemein"
             f"{', ' + current_user.department if current_user.department else ''}"
             f"{', ' + current_user.assigned_project if current_user.assigned_project else ''}. "
             "doc.content (echter Text) wird geladen.")

    log_step("AIService", "Database",
             "Säule A: Conversation History",
             f"Letzte {5} ChatMessages aus DB. .desc() → reversed() → chronologische Reihenfolge.")

    log_step("AIService", "OpenAI",
             "Säule B + API-Call",
             "System-Prompt mit Rolle/Abteilung (Pillar B) + History + RAG-Kontext → OpenAI.")

    try:
        ai_reply, context_titles = run_rag_chat(current_user, request.question, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {e}")

    log_step("OpenAI", "AIService",
             "KI-Antwort zurück",
             f"Antwort auf Basis von {len(context_titles)} Dokumenten. Keine Halluzinationen.")

    db.add(ChatMessage(
        user_id=current_user.id,
        user_question=request.question,
        ai_response=ai_reply
    ))
    db.commit()

    log_step("AIService", "PostgreSQL",
             "Verlauf gespeichert",
             "ChatMessage in chat_messages-Tabelle persistiert. Für nächste History-Abfrage.")

    log_step("PostgreSQL", "Schema",
             "ChatResponse validieren",
             "Pydantic ChatResponse: user_question, ai_response, used_documents.")

    log_step("Schema", "User",
             "Antwort mit Quellen",
             f"Mitarbeiter erhält KI-Antwort + {len(context_titles)} Quellen: {', '.join(context_titles) or 'keine'}.")

    await manager.broadcast_trace(get_trace(), f"POST /api/chat/ask")
    response.headers["X-Workflow-Trace"] = json.dumps(get_trace())

    return ChatResponse(
        user_question=request.question,
        ai_response=ai_reply,
        used_documents=context_titles
    )


@router.post("/tasks/{task_id}/explain", response_model=TaskExplainEndpointResponse)
async def explain_task_personalized(
    task_id:  int,
    response: Response,
    db:       Session = Depends(get_db),
    user_id:  int     = Depends(get_current_user)
):
    """Task explainer with OpenAI Structured Outputs."""
    start_trace()
    log_step("User", "Main",
             f"POST /api/chat/tasks/{task_id}/explain",
             "Mitarbeiter möchte eine Aufgabe erklärt bekommen.")
    log_step("Main", "Security",
             "get_current_user()",
             "x-user-id Header extrahiert. Kein DB-Zugriff in get_current_user.")
    log_step("Security", "Router",
             "Routing zu chat.py",
             "load_current_user() lädt User mit bestehender Session.")

    current_user = load_current_user(user_id, db)
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found!")

    if db_task.assigned_to != current_user.id and current_user.user_role == "Mitarbeiter":
        raise HTTPException(status_code=403, detail="You can only explain your own tasks!")

    log_step("Router", "AIService",
             "run_task_explanation()",
             f"Task '{db_task.title}' wird erklärt für "
             f"'{current_user.username}' (Rolle: {current_user.user_role}).")

    log_step("AIService", "OpenAI",
             "Structured Outputs .parse()",
             "beta.chat.completions.parse() mit TaskExplanationLLMResponse Schema. "
             "Modell muss exakt summary + steps + tools_and_tips zurückgeben.")

    try:
        parsed = run_task_explanation(current_user, db_task, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {e}")

    log_step("OpenAI", "Schema",
             "Garantiertes JSON zurück",
             f"Felder können nicht fehlen. steps={len(parsed.steps)} Schritte, "
             f"tools_and_tips={len(parsed.tools_and_tips)} Tipps.")

    log_step("Schema", "User",
             "TaskExplainEndpointResponse",
             "Typisiertes Pydantic-Objekt – kein roher Dict. Frontend kann steps[0] direkt aufrufen.")

    await manager.broadcast_trace(get_trace(), f"POST /api/chat/tasks/{task_id}/explain")
    response.headers["X-Workflow-Trace"] = json.dumps(get_trace())

    return TaskExplainEndpointResponse(
        task_id=task_id,
        task_title=db_task.title,
        explanation=parsed
    )