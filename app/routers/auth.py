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
    """Creates a new user with live trace broadcast."""
    start_trace()
    log_step("User", "Main",
             "POST /api/auth/register",
             f"Admin registriert neuen User '{user.username}' "
             f"(Rolle: {user.user_role}, Abteilung: {user.department or 'keine'}).")

    log_step("Main", "Security",
             "Admin-Token Guard",
             "dependencies=[Depends(verify_admin_token)] prüft x-admin-token Header "
             "bevor der Endpoint überhaupt läuft.")

    log_step("Security", "Schema",
             "Pydantic validiert Input",
             f"UserCreate: EmailStr prüft E-Mail-Format, "
             f"Literal[...] prüft Rolle '{user.user_role}', "
             f"min_length=6 prüft Passwort. 422 bei ungültigen Werten.")

    log_step("Schema", "Router",
             "Routing zu auth.py",
             "Alle Eingaben valide – register_user() übernimmt die Business-Logik.")

    # Check username
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered!")

    log_step("Router", "PostgreSQL",
             "Duplikat-Check Username",
             f"SELECT * FROM users WHERE username='{user.username}' → nicht gefunden. OK.")

    # Check email
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered!")

    log_step("PostgreSQL", "Router",
             "Duplikat-Check Email",
             f"SELECT * FROM users WHERE email='{user.email}' → nicht gefunden. OK.")

    log_step("Router", "Security",
             "Passwort hashen",
             "hash_password() → pwd_context.hash() → bcrypt mit zufälligem Salt. "
             "Ergebnis: 60-Zeichen Hash. Niemals Klartext in DB.")

    hashed = hash_password(user.password)

    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed,
        user_role=user.user_role,
        assigned_project=user.assigned_project,
        department=user.department,
        reports_to=user.reports_to
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_step("Security", "Database",
             "User in DB anlegen",
             f"db.add(new_user) → db.commit() → db.refresh(). "
             f"Neuer User id={new_user.id} erstellt.")

    log_step("Database", "Schema",
             "UserResponse validieren",
             "Pydantic UserResponse: password und password_hash werden "
             "NICHT zurückgegeben – nur sichere Felder.")

    log_step("Schema", "User",
             "201 Created",
             f"Admin erhält User-Daten ohne Passwort. "
             f"User '{new_user.username}' kann sich jetzt einloggen.")

    await manager.broadcast_trace(get_trace(), "POST /api/auth/register")
    response.headers["X-Workflow-Trace"] = json.dumps(get_trace())
    return new_user