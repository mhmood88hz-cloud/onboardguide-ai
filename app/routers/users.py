from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.security import verify_admin_token

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.delete("/{user_id}", status_code=200,
               dependencies=[Depends(verify_admin_token)])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    Deletes a user. Database-level constraints handle related data:
    - tasks.assigned_to   → CASCADE  (orphaned tasks deleted)
    - tasks.assigned_by   → SET NULL (task remains, creator reference = NULL)
    - documents.uploaded_by → SET NULL (documents preserved)
    - chat_messages       → CASCADE  (chat history deleted)
    - users.reports_to    → SET NULL (team members remain)
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found!")

    info = {
        "deleted_user_id": db_user.id,
        "deleted_username": db_user.username,
        "deleted_email":    db_user.email,
        "deleted_role":     db_user.user_role,
    }

    # synchronize_session="fetch" delegates cascade to PostgreSQL directly
    # avoids SQLAlchemy trying to set assigned_to=NULL (NOT NULL constraint crash)
    db.query(User).filter(User.id == user_id).delete(synchronize_session="fetch")
    db.commit()
    return {"status": "success", "message": f"User '{info['deleted_username']}' deleted.", **info}