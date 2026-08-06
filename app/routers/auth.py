import json
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse, LoginRequest, TokenResponse, ChangePasswordRequest, ResetPasswordRequest
from app.security import require_verwaltung, hash_password, verify_password, create_access_token, get_current_user, load_current_user
from app.services.trace import start_trace, log_step, get_trace
from app.services.ws_manager import manager

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):

    # Find user by username
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Benutzername oder Passwort falsch.")

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Benutzername oder Passwort falsch.")

    # Create JWT token
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.user_role
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        user_role=user.user_role
    )
@router.post("/change-password", status_code=200)
def change_password(
    request: ChangePasswordRequest,
    db:      Session = Depends(get_db),
    user_id: int     = Depends(get_current_user)
):
    """
    Mitarbeiter ändert sein eigenes Passwort.
    Benötigt: JWT Token + altes Passwort als Beweis.
    """
    current_user = load_current_user(user_id, db)

    if not verify_password(request.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=400,
            detail="Altes Passwort ist falsch."
        )

    current_user.password_hash = hash_password(request.new_password)
    db.commit()

    return {
        "status":  "success",
        "message": f"Passwort von '{current_user.username}' erfolgreich geändert."
    }


@router.post("/reset-password", status_code=200,
             dependencies=[Depends(require_verwaltung)])
def reset_password(
    request: ResetPasswordRequest,
    db:      Session = Depends(get_db)
):
    """
    Verwaltung setzt Passwort eines Mitarbeiters zurück.
    Benötigt: JWT Token mit Verwaltung-Rolle.
    """
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden!")

    user.password_hash = hash_password(request.new_password)
    db.commit()

    return {
        "status":  "success",
        "message": f"Passwort von '{user.username}' wurde zurückgesetzt."
    }

@router.post("/register", response_model=UserResponse, status_code=201,
             dependencies=[Depends(require_verwaltung)])
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
             "verify_admin_token prüft den x-admin-token Header.")
    log_step("Security", "Schema",
             "Pydantic validiert Eingabe",
             f"UserCreate: EmailStr, Literal-Rolle '{user.user_role}', min_length Passwort.")
    log_step("Schema", "Router",
             "Weiterleitung zu auth.py",
             "Alle Eingaben valide – register_user() übernimmt.")

    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Benutzername bereits vergeben!")
    log_step("Router", "PostgreSQL",
             "Duplikat-Prüfung Benutzername",
             f"Username '{user.username}' → nicht gefunden. OK.")

    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert!")
    log_step("PostgreSQL", "Router",
             "Duplikat-Prüfung E-Mail",
             f"E-Mail '{user.email}' → nicht gefunden. OK.")

    log_step("Router", "Security",
             "Passwort hashen",
             "bcrypt mit zufälligem Salt → 60-Zeichen Hash.")

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
             "Benutzer in DB angelegt",
             f"id={new_user.id}, Passwort als Hash gespeichert.")
    log_step("Database", "Schema",
             "UserResponse validieren",
             "password_hash wird NICHT zurückgegeben.")
    log_step("Schema", "User",
             "201 Erstellt",
             f"Benutzer '{new_user.username}' erfolgreich angelegt.")

    await manager.broadcast_trace(get_trace(), "POST /api/auth/register")
    response.headers["X-Workflow-Trace"] = json.dumps(get_trace())
    return new_user