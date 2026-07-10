import json
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Task
from app.schemas import TaskCreate, TaskResponse
from app.security import get_current_user, load_current_user
from app.services.trace import start_trace, log_step, get_trace
from app.services.ws_manager import manager

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


def update_user_progress(db: Session, user_id: int):
    """Recalculates progress_percent after any task change."""
    user_tasks = db.query(Task).filter(Task.assigned_to == user_id).all()
    new_progress = 0 if not user_tasks else int(
        sum(1 for t in user_tasks if t.is_completed) / len(user_tasks) * 100
    )
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.progress_percent = new_progress
        db.commit()
        db.refresh(db_user)


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Creates a new task – no trace needed for simple CRUD."""
    if not db.query(User).filter(User.id == task.assigned_to).first():
        raise HTTPException(status_code=404, detail="Assigned user not found!")
    new_task = Task(**task.model_dump())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    update_user_progress(db, task.assigned_to)
    db.refresh(new_task)
    return new_task


@router.get("", response_model=List[TaskResponse])
def get_user_tasks(user_id: int, db: Session = Depends(get_db)):
    if not db.query(User).filter(User.id == user_id).first():
        raise HTTPException(status_code=404, detail="User not found!")
    return db.query(Task).filter(Task.assigned_to == user_id).all()


@router.put("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id:  int,
    response: Response,
    db:       Session = Depends(get_db),
    user_id:  int     = Depends(get_current_user)
):
    """
    Marks a task as completed with full ownership validation.
    Broadcasts live trace to simulator.
    """
    start_trace()
    log_step("User", "Main",
             f"PUT /api/tasks/{task_id}/complete",
             "User möchte einen Task abschließen. x-user-id Header mitgeschickt.")
    log_step("Main", "Security",
             "get_current_user()",
             "Nur Header-Extraktion – kein DB-Zugriff. Gibt int zurück.")
    log_step("Security", "Router",
             "Routing zu tasks.py",
             "load_current_user() lädt User-Objekt mit bestehender Session.")

    current_user = load_current_user(user_id, db)

    log_step("Router", "PostgreSQL",
             "Task aus DB laden",
             f"db.query(Task).filter(Task.id == {task_id}).first()")

    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found!")

    assignee = db.query(User).filter(User.id == db_task.assigned_to).first()

    log_step("PostgreSQL", "Security",
             "Berechtigungsprüfung",
             f"Formel: (U_id == T_assigned_to) ∨ (Verwaltung) ∨ (Leader ∧ reports_to). "
             f"Aktueller User: '{current_user.username}' (Rolle: {current_user.user_role}).")

    is_assigned  = (current_user.id == db_task.assigned_to)
    is_hr        = (current_user.user_role == "Verwaltung")
    is_leader    = (assignee and assignee.reports_to == current_user.id
                    and current_user.user_role == "Leader")

    if not (is_assigned or is_hr or is_leader):
        raise HTTPException(
            status_code=403,
            detail="Not authorized. Only assigned employee, HR or direct leader."
        )

    log_step("Security", "Router",
             "✅ Berechtigt",
             f"{'Zugewiesener Mitarbeiter' if is_assigned else 'HR-Admin' if is_hr else 'Direkter Leader'} "
             f"– Zugriff erlaubt.")

    if db_task.is_completed:
        log_step("Router", "Schema",
                 "Bereits erledigt",
                 "Task war schon completed – idempotent, keine Änderung.")
        log_step("Schema", "User", "200 OK", "Unveränderter Task zurückgegeben.")
        await manager.broadcast_trace(get_trace(), f"PUT /api/tasks/{task_id}/complete")
        return db_task

    db_task.is_completed = True
    db_task.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_task)

    log_step("Router", "Database",
             "Task als erledigt markiert",
             f"is_completed=True, completed_at={db_task.completed_at.strftime('%H:%M:%S UTC')}. "
             "db.commit() + db.refresh().")

    update_user_progress(db, db_task.assigned_to)
    db.refresh(db_task)

    log_step("Database", "PostgreSQL",
             "Fortschritt neu berechnet",
             f"update_user_progress() → (erledigte/alle Tasks)*100. "
             f"progress_percent von User {db_task.assigned_to} aktualisiert.")

    log_step("PostgreSQL", "Schema",
             "TaskResponse validieren",
             "Pydantic TaskResponse mit is_completed=True und completed_at Zeitstempel.")

    log_step("Schema", "User",
             "200 OK – Task erledigt",
             "User sieht aktualisierten Task. Fortschritt wurde automatisch neu berechnet.")

    await manager.broadcast_trace(get_trace(), f"PUT /api/tasks/{task_id}/complete")
    response.headers["X-Workflow-Trace"] = json.dumps(get_trace())
    return db_task


@router.get("/leader/progress")
def get_leader_team_progress(leader_id: int, db: Session = Depends(get_db)):
    leader = db.query(User).filter(User.id == leader_id, User.user_role == "Leader").first()
    if not leader:
        raise HTTPException(status_code=404, detail="Team leader not found!")
    return db.query(User).filter(User.reports_to == leader_id).all()