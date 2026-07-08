from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ChatMessage
from app.schemas import ChatRequest, ChatResponse, TaskExplainEndpointResponse
from app.security import get_current_user, load_current_user
from app.services.ai_service import run_rag_chat, run_task_explanation

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/ask", response_model=ChatResponse)
def ask_onboarding_guide(
    request: ChatRequest,
    db:      Session = Depends(get_db),
    user_id: int     = Depends(get_current_user)
):
    """
    Onboarding chatbot using all three prompt engineering pillars:
    - Pillar A: Conversation History
    - Pillar B: Dynamic Context Injection
    - Pillar C: RAG (doc.content as source of truth)
    """
    current_user = load_current_user(user_id, db)

    try:
        ai_reply, context_titles = run_rag_chat(current_user, request.question, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {str(e)}")

    # Persist conversation turn for use as history in next request
    db.add(ChatMessage(
        user_id=current_user.id,
        user_question=request.question,
        ai_response=ai_reply
    ))
    db.commit()

    return ChatResponse(
        user_question=request.question,
        ai_response=ai_reply,
        used_documents=context_titles
    )


@router.post("/tasks/{task_id}/explain", response_model=TaskExplainEndpointResponse)
def explain_task_personalized(
    task_id: int,
    db:      Session = Depends(get_db),
    user_id: int     = Depends(get_current_user)
):
    """
    Explains a task step by step using OpenAI Structured Outputs.
    Guarantees fields: summary, steps, tools_and_tips.
    """
    from app.models import Task
    current_user = load_current_user(user_id, db)

    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found!")

    if db_task.assigned_to != current_user.id and current_user.user_role == "Mitarbeiter":
        raise HTTPException(status_code=403, detail="You can only explain your own tasks!")

    try:
        parsed = run_task_explanation(current_user, db_task, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI Structured Output error: {str(e)}")

    return TaskExplainEndpointResponse(
        task_id=task_id,
        task_title=db_task.title,
        explanation=parsed
    )