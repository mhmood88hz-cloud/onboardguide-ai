import json
import re
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Organization
from app.schemas import (
    UserCreate, UserResponse, LoginRequest, TokenResponse,
    ChangePasswordRequest, ResetPasswordRequest, SignupRequest,
)
from app.security import require_verwaltung, hash_password, verify_password, create_access_token, get_current_user, load_current_user
from app.services.trace import start_trace, log_step, get_trace
from app.services.ws_manager import manager

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "firma"
    return base


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
        user_role=user.user_role,
        organization_id=user.organization_id,
        organization_name=user.organization.name
    )


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """
    Self-Serve-Registrierung für eine neue Firma: legt die Organization an
    und macht den anfragenden Nutzer zu deren erstem Verwaltung-Account.
    Kein Login/Token nötig – das ist der Einstiegspunkt für neue Kunden.
    """
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(status_code=400, detail="Benutzername bereits vergeben!")
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert!")

    slug = base_slug = _slugify(request.organization_name)
    suffix = 2
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    org = Organization(name=request.organization_name, slug=slug)
    db.add(org)
    db.flush()  # org.id verfügbar, ohne die Transaktion schon zu committen

    admin_user = User(
        organization_id=org.id,
        username=request.username,
        email=request.email,
        password_hash=hash_password(request.password),
        user_role="Verwaltung",
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    token = create_access_token(
        user_id=admin_user.id,
        username=admin_user.username,
        role=admin_user.user_role
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=admin_user.id,
        username=admin_user.username,
        user_role=admin_user.user_role,
        organization_id=org.id,
        organization_name=org.name
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


@router.post("/reset-password", status_code=200)
def reset_password(
    request:      ResetPasswordRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_verwaltung)
):
    """
    Verwaltung setzt Passwort eines Mitarbeiters zurück.
    Benötigt: JWT Token mit Verwaltung-Rolle, Ziel-Nutzer muss zur selben Firma gehören.
    """
    user = db.query(User).filter(
        User.id == request.user_id,
        User.organization_id == current_user.organization_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden!")

    user.password_hash = hash_password(request.new_password)
    db.commit()

    return {
        "status":  "success",
        "message": f"Passwort von '{user.username}' wurde zurückgesetzt."
    }

@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(
    user:         UserCreate,
    response:     Response,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_verwaltung)
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

    if user.reports_to is not None:
        manager_user = db.query(User).filter(
            User.id == user.reports_to,
            User.organization_id == current_user.organization_id
        ).first()
        if not manager_user:
            raise HTTPException(status_code=404, detail="reports_to: Benutzer nicht in dieser Firma gefunden!")

    log_step("Router", "Security",
             "Passwort hashen",
             "bcrypt mit zufälligem Salt → 60-Zeichen Hash.")

    new_user = User(
        organization_id=current_user.organization_id,
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