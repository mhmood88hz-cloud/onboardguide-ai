from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Task
from app.schemas import TaskCreate, TaskResponse
from app.security import get_current_user, load_current_user

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


def update_user_progress(db: Session, user_id: int):
    """
    Automatically recalculates progress_percent after any task change.
    Formula: (completed tasks / total tasks) * 100
    """
    user_tasks = db.query(Task).filter(Task.assigned_to == user_id).all()
    if not user_tasks:
        new_progress = 0
    else:
        completed    = sum(1 for t in user_tasks if t.is_completed)
        new_progress = int((completed / len(user_tasks)) * 100)

    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.progress_percent = new_progress
        db.commit()
        db.refresh(db_user)


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Creates a new task and recalculates the assigned user's progress."""
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
    """Returns all tasks assigned to a specific user."""
    if not db.query(User).filter(User.id == user_id).first():
        raise HTTPException(status_code=404, detail="User not found!")
    return db.query(Task).filter(Task.assigned_to == user_id).all()


@router.put("/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: int,
    db:      Session = Depends(get_db),
    user_id: int     = Depends(get_current_user)
):
    """
    Marks a task as completed. Enforces role-based ownership validation.

    Permission formula:
    Allowed iff:
        (current_user.id == task.assigned_to)           # assigned employee
        OR (current_user.role == 'Verwaltung')           # HR admin
        OR (current_user.role == 'Leader'
            AND assignee.reports_to == current_user.id)  # direct team leader
    """
    current_user = load_current_user(user_id, db)

    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found!")

    assignee = db.query(User).filter(User.id == db_task.assigned_to).first()

    is_assigned_user = (current_user.id == db_task.assigned_to)
    is_hr            = (current_user.user_role == "Verwaltung")
    is_direct_leader = (
        assignee is not None
        and assignee.reports_to == current_user.id
        and current_user.user_role == "Leader"
    )

    if not (is_assigned_user or is_hr or is_direct_leader):
        raise HTTPException(
            status_code=403,
            detail=(
                "Not authorized. Only the assigned employee, "
                "an HR administrator, or the direct team leader may complete this task."
            )
        )

    if db_task.is_completed:
        return db_task

    db_task.is_completed = True
    db_task.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_task)

    update_user_progress(db, db_task.assigned_to)
    db.refresh(db_task)
    return db_task


@router.get("/leader/progress")
def get_leader_team_progress(leader_id: int, db: Session = Depends(get_db)):
    """Returns all team members reporting to the given leader with their progress."""
    leader = db.query(User).filter(User.id == leader_id, User.user_role == "Leader").first()
    if not leader:
        raise HTTPException(status_code=404, detail="Team leader not found!")
    return db.query(User).filter(User.reports_to == leader_id).all()