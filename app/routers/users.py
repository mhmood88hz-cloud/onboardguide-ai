import json
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.security import verify_admin_token
from app.services.trace import start_trace, log_step, get_trace
from app.services.ws_manager import manager

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.delete("/{user_id}", status_code=200,
               dependencies=[Depends(verify_admin_token)])
async def delete_user(
    user_id:  int,
    response: Response,
    db:       Session = Depends(get_db)
):
    """Deletes a user with cascade logic and live trace broadcast."""
    start_trace()
    log_step("User", "Main",
             f"DELETE /api/users/{user_id}",
             f"Admin möchte User id={user_id} löschen.")

    log_step("Main", "Security",
             "Admin-Token Guard",
             "dependencies=[Depends(verify_admin_token)] – nur mit gültigem Token.")

    log_step("Security", "Router",
             "Routing zu users.py",
             "Token gültig – delete_user() übernimmt.")

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found!")

    log_step("Router", "PostgreSQL",
             "User in DB suchen",
             f"SELECT * FROM users WHERE id={user_id} → gefunden: '{db_user.username}'.")

    info = {
        "deleted_user_id": db_user.id,
        "deleted_username": db_user.username,
        "deleted_email":    db_user.email,
        "deleted_role":     db_user.user_role,
    }

    log_step("PostgreSQL", "Database",
             "Cascade-Logik prüfen",
             "tasks.assigned_to → CASCADE (Tasks gelöscht). "
             "documents.uploaded_by → SET NULL (Dokumente bleiben). "
             "chat_messages → CASCADE (Verlauf gelöscht). "
             "users.reports_to → SET NULL (Team-Mitglieder bleiben).")

    # synchronize_session="fetch" delegates cascade to PostgreSQL directly
    db.query(User).filter(User.id == user_id).delete(synchronize_session="fetch")
    db.commit()

    log_step("Database", "PostgreSQL",
             "DELETE ausgeführt",
             f"synchronize_session='fetch' delegiert CASCADE direkt an PostgreSQL. "
             f"db.delete(user) würde assigned_to=NULL setzen → NOT NULL Crash.")

    log_step("PostgreSQL", "Schema",
             "Cascade abgeschlossen",
             "Tasks des Users gelöscht. Dokumente erhalten (uploaded_by=NULL). "
             "Chat-Verlauf bereinigt.")

    log_step("Schema", "User",
             "200 OK – User gelöscht",
             f"Admin erhält Bestätigung: '{info['deleted_username']}' "
             f"(id={info['deleted_user_id']}) wurde erfolgreich entfernt.")

    await manager.broadcast_trace(get_trace(), f"DELETE /api/users/{user_id}")
    response.headers["X-Workflow-Trace"] = json.dumps(get_trace())

    return {
        "status":  "success",
        "message": f"User '{info['deleted_username']}' deleted.",
        **info
    }