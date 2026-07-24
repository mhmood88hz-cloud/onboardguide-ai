import json
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ChatMessage, Task
from app.schemas import ChatRequest, ChatResponse, TaskExplainEndpointResponse
from app.security import get_current_user, load_current_user
from app.services.ai_service import run_rag_chat, run_task_explanation, run_model_comparison
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
    start_trace()
    log_step("User", "Main",
             "POST /api/chat/ask",
             f"Mitarbeiter stellt eine Frage: '{request.question[:60]}...'")
    log_step("Main", "Security",
             "get_current_user()",
             "x-user-id Header wird extrahiert. Gibt nur int zurück – kein DB-Zugriff.")
    log_step("Security", "Router",
             "Weiterleitung zu chat.py",
             "load_current_user() lädt Benutzer-Objekt mit bestehender Session.")

    current_user = load_current_user(user_id, db)

    log_step("Router", "AIService",
             "run_rag_chat() gestartet",
             f"ai_service.py übernimmt für '{current_user.username}' "
             f"(Rolle: {current_user.user_role}, Abteilung: {current_user.department or 'Allgemein'}).")
    log_step("AIService", "PostgreSQL",
             "Säule C: Vektor-Ähnlichkeitssuche",
             "Frage wird in Einbettung umgewandelt → pgvector Cosine-Suche → "
             "Top-3 relevanteste Chunks werden gefunden.")
    log_step("AIService", "Database",
             "Säule A: Gesprächsverlauf laden",
             "Letzte 5 ChatMessages aus der Datenbank geladen.")
    log_step("AIService", "OpenAI",
             "Säule B + API-Aufruf",
             "System-Prompt (Säule B) + Verlauf + RAG-Chunks → OpenAI.")

    try:
        if request.compare_models:
            ai_reply, context_titles, chunk_stats, model_comparison = \
                run_model_comparison(current_user, request.question, db)
        else:
            ai_reply, context_titles, chunk_stats = run_rag_chat(
                current_user, request.question, db
            )
            model_comparison = []
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"OpenAI Fehler: {str(e)}")

    chunk_info = " | ".join(
        f"Chunk {c['chunk_index']} Score:{c['similarity_score']}"
        for c in chunk_stats
    )
    log_step("OpenAI", "AIService",
             "KI-Antwort erhalten",
             f"Antwort basiert auf {len(chunk_stats)} Chunks. "
             f"Scores: {chunk_info or 'keine'}")

    db.add(ChatMessage(
        user_id=current_user.id,
        user_question=request.question,
        ai_response=ai_reply
    ))
    db.commit()

    log_step("AIService", "PostgreSQL",
             "Gesprächsverlauf gespeichert",
             "ChatMessage in chat_messages-Tabelle gespeichert. "
             "Für die nächste History-Abfrage verfügbar.")
    log_step("PostgreSQL", "Schema",
             "ChatResponse validieren",
             "Pydantic ChatResponse: Frage, Antwort, Quellen, Chunk-Scores.")
    log_step("Schema", "User",
             "Antwort mit Quellen und Metriken",
             f"Mitarbeiter erhält Antwort + {len(context_titles)} Quellen "
             f"+ {len(chunk_stats)} Chunk-Ähnlichkeitswerte.")

    await manager.broadcast_trace(
        trace    = get_trace(),
        endpoint = "POST /api/chat/ask",
        extras   = {
            "chunk_stats":      chunk_stats,
            "model_comparison": model_comparison
        }
    )
    response.headers["X-Workflow-Trace"] = json.dumps(get_trace())

    return ChatResponse(
        user_question=request.question,
        ai_response=ai_reply,
        used_documents=context_titles,
        chunk_stats=chunk_stats,
        model_comparison=model_comparison
    )


@router.post("/tasks/{task_id}/explain",
             response_model=TaskExplainEndpointResponse)
async def explain_task_personalized(
    task_id:  int,
    response: Response,
    db:       Session = Depends(get_db),
    user_id:  int     = Depends(get_current_user)
):
    start_trace()
    log_step("User", "Main",
             f"POST /api/chat/tasks/{task_id}/explain",
             "Mitarbeiter möchte eine Aufgabe erklärt bekommen.")
    log_step("Main", "Security",
             "get_current_user()",
             "x-user-id Header extrahiert. Kein DB-Zugriff in get_current_user.")
    log_step("Security", "Router",
             "Weiterleitung zu chat.py",
             "load_current_user() lädt Benutzer mit bestehender Session.")

    current_user = load_current_user(user_id, db)
    db_task      = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden!")

    if db_task.assigned_to != current_user.id and \
       current_user.user_role == "Mitarbeiter":
        raise HTTPException(
            status_code=403,
            detail="Nur eigene Aufgaben können erklärt werden!"
        )

    log_step("Router", "AIService",
             "run_task_explanation()",
             f"Aufgabe '{db_task.title}' wird erklärt für "
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
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI Fehler: {e}"
        )

    log_step("OpenAI", "Schema",
             "Garantiertes JSON erhalten",
             f"Felder können nicht fehlen. "
             f"steps={len(parsed.steps)} Schritte, "
             f"tools_and_tips={len(parsed.tools_and_tips)} Tipps.")
    log_step("Schema", "User",
             "TaskExplainEndpointResponse",
             "Typisiertes Pydantic-Objekt – Frontend kann steps[0] direkt aufrufen.")

    await manager.broadcast_trace(
        get_trace(),
        f"POST /api/chat/tasks/{task_id}/explain"
    )
    response.headers["X-Workflow-Trace"] = json.dumps(get_trace())

    return TaskExplainEndpointResponse(
        task_id=task_id,
        task_title=db_task.title,
        explanation=parsed
    )