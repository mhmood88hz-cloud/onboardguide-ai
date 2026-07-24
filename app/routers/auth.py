import json
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse
from app.security import verify_admin_token, hash_password
from app.services.trace import start_trace, log_step, get_trace
from app.services.ws_manager import manager

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201,
             dependencies=[Depends(verify_admin_token)])
async def register_user(
    user:     UserCreate,
    response: Response,
    db:       Session = Depends(get_db)
):
    start_trace()
    log_step("User", "Main",
             "POST /api/auth/register",
             f"Admin registriert neuen Benutzer '{user.username}' "
             f"(Rolle: {user.user_role}, Abteilung: {user.department or 'keine'}).")
    log_step("Main", "Security",
             "Admin-Token Prüfung",
             "verify_admin_token prüft den x-admin-token Header "
             "bevor der Endpoint ausgeführt wird.")
    log_step("Security", "Schema",
             "Pydantic validiert Eingabe",
             f"UserCreate: EmailStr prüft E-Mail-Format, "
             f"Literal prüft Rolle '{user.user_role}', "
             f"min_length=6 prüft Passwort. 422 bei ungültigen Werten.")
    log_step("Schema", "Router",
             "Weiterleitung zu auth.py",
             "Alle Eingaben valide – register_user() übernimmt die Logik.")

    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Benutzername bereits vergeben!")
    log_step("Router", "PostgreSQL",
             "Duplikat-Prüfung Benutzername",
             f"SELECT * FROM users WHERE username='{user.username}' → nicht gefunden. OK.")

    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert!")
    log_step("PostgreSQL", "Router",
             "Duplikat-Prüfung E-Mail",
             f"SELECT * FROM users WHERE email='{user.email}' → nicht gefunden. OK.")

    log_step("Router", "Security",
             "Passwort hashen",
             "hash_password() → bcrypt mit zufälligem Salt. "
             "Ergebnis: 60-Zeichen Hash. Niemals Klartext in der Datenbank.")

    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password),
        user_role=user.user_role,
        assigned_project=user.assigned_project,
        department=user.department,
        reports_to=user.reports_to
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_step("Security", "Database",
             "Benutzer in DB anlegen",
             f"db.add(new_user) → db.commit() → db.refresh(). "
             f"Neuer Benutzer id={new_user.id} erstellt.")
    log_step("Database", "Schema",
             "UserResponse validieren",
             "Pydantic UserResponse: Passwort und password_hash werden "
             "NICHT zurückgegeben – nur sichere Felder.")
    log_step("Schema", "User",
             "201 Erstellt",
             f"Admin erhält Benutzerdaten ohne Passwort. "
             f"Benutzer '{new_user.username}' kann sich jetzt einloggen.")

    await manager.broadcast_trace(get_trace(), "POST /api/auth/register")
    response.headers["X-Workflow-Trace"] = json.dumps(get_trace())
    return new_user