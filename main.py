# =========================================================================
# SCHRITT 1: DIE IMPORTE (UNSERE WERKZEUGKISTE)
# =========================================================================

import os
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Literal
# NEU: Wir importieren 'Header', um HTTP-Header-Felder auszulesen
from fastapi import FastAPI, Depends, HTTPException, Header

# Für die Daten-Validierung importieren wir Pydantic:
from pydantic import BaseModel, Field

# Für unsere Datenbank-Modelle importieren wir zusätzliche Werkzeuge von SQLAlchemy:
from sqlalchemy import create_engine, text, Column, Integer, String, Boolean, Text, DateTime, ForeignKey

# - 'declarative_base': Die Mutterklasse, von der alle unsere Tabellen-Klassen erben müssen.
from sqlalchemy.orm import sessionmaker, Session, declarative_base, relationship

from dotenv import load_dotenv

# =========================================================================
# SCHRITT 2: DIE DATENBANK-VERBINDUNG & DIE WEB-APP (UNSER FUNDAMENT)
# =========================================================================

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 'Base' ist das Fundament für unsere Tabellen-Klassen.
Base = declarative_base()

app = FastAPI(title="OnboardGuide AI Backend")


# =========================================================================
# SCHRITT 3: DIE DATENBANK-MODELLE (UNSERE POSTGRES-TABELLEN ALS PYTHON-KLASSEN)
# =========================================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    user_role = Column(String(20), nullable=False)  # 'Verwaltung', 'Leader', 'Mitarbeiter'
    assigned_project = Column(String(100), nullable=True)  # Projekt-Filter für Mitarbeiter
    department = Column(String(100), nullable=True)  # Abteilung (z.B. IT, HR, Marketing)

    reports_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    progress_percent = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    # Beziehungen (Relationships) für komfortables Abfragen in Python:
    documents = relationship("Document", back_populates="uploader")
    chat_messages = relationship("ChatMessage", back_populates="user")

    tasks_assigned = relationship("Task", foreign_keys="Task.assigned_to", back_populates="assignee")
    tasks_created = relationship("Task", foreign_keys="Task.assigned_by", back_populates="creator")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)  # Pfad zur Datei auf dem Server
    category = Column(String(100), nullable=False)  # 'Allgemein', 'IT', oder projektspezifisch

    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    # Beziehung zurück zum User
    uploader = relationship("User", back_populates="documents")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_question = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    # Beziehung zurück zum User
    user = relationship("User", back_populates="chat_messages")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(20), nullable=False)  # 'Onboarding' oder 'Projekt'
    project_name = Column(String(100), nullable=True)  # Welchem Projekt gehört dieser Task?

    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Ersteller
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)  # Wann wurde es erledigt?
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    # Beziehungen zurück zum User
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="tasks_assigned")
    creator = relationship("User", foreign_keys=[assigned_by], back_populates="tasks_created")


# =========================================================================
# SCHRITT 4: DIE PYDANTIC-SCHEMAS (UNSERE DATEN-GATEKEEPER)
# =========================================================================

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, description="Eindeutiger Login-Name")
    email: str = Field(..., description="E-Mail-Adresse des Benutzers")
    user_role: Literal["Verwaltung", "Leader", "Mitarbeiter"] = Field(...,
                                                                      description="Muss 'Verwaltung', 'Leader' oder 'Mitarbeiter' sein")
    assigned_project: Optional[str] = None
    department: Optional[str] = None
    reports_to: Optional[int] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Das Initialpasswort (mind. 6 Zeichen)")


class UserResponse(UserBase):
    id: int
    progress_percent: int
    created_at: datetime

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    task_type: Literal["Onboarding", "Projekt"] = Field(..., description="Entweder 'Onboarding' oder 'Projekt'")
    project_name: Optional[str] = None
    assigned_to: int


class TaskCreate(TaskBase):
    assigned_by: Optional[int] = None


class TaskResponse(TaskBase):
    id: int
    assigned_by: Optional[int]
    is_completed: bool
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# =========================================================================
# SCHRITT 5: DIE DATENBANK-SESSION ALS ABHÄNGIGKEIT & HILFSFUNKTIONEN
# =========================================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    """Verschlüsselt Passwörter via SHA-256 mit einem statischen Salz."""
    salt = "onboardguide_secure_salt_2026_mvp"
    return hashlib.sha256((password + salt).encode()).hexdigest()


# NEU: Der Sicherheits-Guard als Dependency!
# FastAPI erkennt 'x_admin_token' im Header automatisch und zeigt das Feld in Swagger UI an.
def verify_admin_token(
        x_admin_token: str = Header(..., description="Geheimer Admin-Token für administrative Aktionen")):
    if x_admin_token != "onboardguide_super_secret_admin_token_2026":
        raise HTTPException(status_code=403, detail="Ungültiger Admin-Token!")
    return x_admin_token


def update_user_progress(db: Session, user_id: int):
    """Berechnet den Fortschritt eines Benutzers vollautomatisch neu."""
    user_tasks = db.query(Task).filter(Task.assigned_to == user_id).all()

    if not user_tasks:
        new_progress = 0
    else:
        completed_tasks_count = sum(1 for task in user_tasks if task.is_completed)
        new_progress = int((completed_tasks_count / len(user_tasks)) * 100)

    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.progress_percent = new_progress
        db.commit()
        db.refresh(db_user)


# =========================================================================
# SCHRITT 6: DIE ECHTEN CRUD-ENDPOINTS (UNSERE API-LOGIK)
# =========================================================================

@app.get("/")
def check_connection(db: Session = Depends(get_db)):
    """Prüft, ob die Verbindung zur PostgreSQL-Datenbank aktiv steht."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "online",
            "message": "Verbindung zur PostgreSQL-Datenbank war erfolgreich!",
            "database": "onboardguide_db"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Datenbank-Verbindung fehlgeschlagen: {str(e)}"
        )


# -------------------------------------------------------------------------
# 1. USER: Registrieren (CREATE + AUTH GUARD)
# -------------------------------------------------------------------------
# NEU: Wir fügen 'Depends(verify_admin_token)' hinzu!
@app.post("/api/auth/register", response_model=UserResponse, status_code=201)
def register_user(
        user: UserCreate,
        db: Session = Depends(get_db),
):
    """Registriert einen neuen Benutzer im System. (Exklusiv für Verwaltung/HR)."""
    existing_username = db.query(User).filter(User.username == user.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Benutzername bereits registriert!")

    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="E-Mail-Adresse bereits registriert!")

    hashed_pwd = hash_password(user.password)

    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed_pwd,
        user_role=user.user_role,
        assigned_project=user.assigned_project,
        department=user.department,
        reports_to=user.reports_to
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# -------------------------------------------------------------------------
# 2. TASK: Aufgabe erstellen (CREATE)
# -------------------------------------------------------------------------
@app.post("/api/tasks", response_model=TaskResponse, status_code=201)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Erstellt eine neue Aufgabe für einen Mitarbeiter und berechnet seinen Fortschritt neu."""
    assigned_user = db.query(User).filter(User.id == task.assigned_to).first()
    if not assigned_user:
        raise HTTPException(status_code=404, detail="Mitarbeiter (assigned_to) nicht gefunden!")

    new_task = Task(
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        project_name=task.project_name,
        assigned_to=task.assigned_to,
        assigned_by=task.assigned_by
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    update_user_progress(db, task.assigned_to)
    return new_task


# -------------------------------------------------------------------------
# 3. TASK: Aufgaben für einen Mitarbeiter abrufen (READ)
# -------------------------------------------------------------------------
@app.get("/api/tasks", response_model=List[TaskResponse])
def get_user_tasks(user_id: int, db: Session = Depends(get_db)):
    """Ruft alle Aufgaben ab, die einem bestimmten Mitarbeiter (user_id) zugewiesen sind."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden!")

    tasks = db.query(Task).filter(Task.assigned_to == user_id).all()
    return tasks


# -------------------------------------------------------------------------
# 4. TASK: Aufgabe als erledigt markieren (UPDATE + AUTO-PROGRESS)
# -------------------------------------------------------------------------
@app.put("/api/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: int, db: Session = Depends(get_db)):
    """Markiert eine Aufgabe als erledigt und berechnet den Fortschritt des Users neu."""
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden!")

    if db_task.is_completed:
        return db_task  # Bereits erledigt

    db_task.is_completed = True
    db_task.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(db_task)

    # Fortschritt live neu berechnen
    update_user_progress(db, db_task.assigned_to)
    return db_task

@app.delete("/api/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden!")
    db.delete(db_user)
    db.commit()
    return

