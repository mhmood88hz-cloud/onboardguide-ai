# =========================================================================
# SCHRITT 1: DIE IMPORTE (UNSERE WERKZEUGKISTE)
# =========================================================================

import os
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException

# Für die Daten-Validierung importieren wir Pydantic:
# - 'BaseModel': Die Mutterklasse für alle Datenstrukturen, die über die API fließen.
# - 'Field': Erlaubt uns exakte Regeln (z.B. Mindestlänge für Passwörter) festzulegen.
from pydantic import BaseModel, Field

# Für unsere Datenbank-Modelle importieren wir zusätzliche Werkzeuge von SQLAlchemy:
from sqlalchemy import create_engine, text, Column, Integer, String, Boolean, Text, DateTime, ForeignKey

# - 'declarative_base': Die Mutterklasse, von der alle unsere Tabellen-Klassen erben müssen.
# - 'relationship': Ermöglicht es uns, in Python direkt auf verknüpfte Daten zuzugreifen (z.B. user.tasks).
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
# SQLAlchemy nutzt diese Base, um all unsere Modelle im Code zu registrieren.
Base = declarative_base()

app = FastAPI(title="OnboardGuide AI Backend")


# =========================================================================
# SCHRITT 4: DIE DATENBANK-MODELLE (UNSERE POSTGRES-TABELLEN ALS PYTHON-KLASSEN)
# =========================================================================

# -------------------------------------------------------------------------
# 1. DAS USER-MODELL (Tabelle: users)
# -------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key = True, index = True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    user_role = Column(String(20), nullable=False)  # 'Verwaltung', 'Leader', 'Mitarbeiter'
    assigned_project = Column(String(100), nullable=True)  # Projekt-Filter für Mitarbeiter
    department = Column(String(100), nullable=True)  # Abteilung (z.B. IT, HR, Marketing)

    # Selbst-Referenz (Self-Reference): reports_to speichert die ID des zuständigen Teamleiters.
    # ForeignKey("users.id") zeigt auf die ID-Spalte derselben Tabelle.
    reports_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    progress_percent = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    # Beziehungen (Relationships) für komfortables Abfragen in Python:
    documents = relationship("Document", back_populates="uploader")
    chat_messages = relationship("ChatMessage", back_populates="user")

    # Da wir zwei Fremdschlüssel auf die User-Tabelle in 'tasks' haben (assigned_to & assigned_by),
    # müssen wir SQLAlchemy explizit sagen, welche Beziehung zu welchem Fremdschlüssel gehört:
    tasks_assigned = relationship("Task", foreign_keys="[Task.assigned_to]", back_populates="assignee")
    tasks_created = relationship("Task", foreign_keys="[Task.assigned_by]", back_populates="creator")


# -------------------------------------------------------------------------
# 2. DAS DOKUMENTEN-MODELL (Tabelle: documents)
# -------------------------------------------------------------------------
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key = True, index = True)
    title = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)  # Pfad zur Datei auf dem Server
    category = Column(String(100), nullable=False)  # 'Allgemein', 'IT', oder projektspezifisch

    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    # Beziehung zurück zum User
    uploader = relationship("User", back_populates="documents")


# -------------------------------------------------------------------------
# 3. DAS CHAT-NACHRICHTEN-MODELL (Tabelle: chat_messages)
# -------------------------------------------------------------------------
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key = True, index = True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_question = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    # Beziehung zurück zum User
    user = relationship("User", back_populates="chat_messages")


# -------------------------------------------------------------------------
# 4. DAS TASK-MODELL (Tabelle: tasks)
# -------------------------------------------------------------------------
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key = True, index = True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(20), nullable=False)  # 'Onboarding' oder 'Projekt'
    project_name = Column(String(100), nullable=True)  # Welchem Projekt gehört dieser Task?

    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Ersteller
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)  # Wann wurde es erledigt?
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    # Beziehungen zurück zum User (mit Angabe der konkreten Fremdschlüssel)
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="tasks_assigned")
    creator = relationship("User", foreign_keys=[assigned_by], back_populates="tasks_created")


# =========================================================================
# SCHRITT 5: DIE PYDANTIC-SCHEMAS (UNSERE DATEN-GATEKEEPER)
# =========================================================================

# -------------------------------------------------------------------------
# 1. USER-SCHEMAS (Eingabe vs. Ausgabe)
# -------------------------------------------------------------------------
class UserBase(BaseModel):
    """Gemeinsame Felder für alle User-Aktionen."""
    username: str = Field(..., min_length=3, max_length=100, description="Eindeutiger Login-Name")
    email: str = Field(..., description="E-Mail-Adresse des Benutzers")
    user_role: str = Field(..., description="Muss 'Verwaltung', 'Leader' oder 'Mitarbeiter' sein")
    assigned_project: Optional[str] = None
    department: Optional[str] = None
    reports_to: Optional[int] = None


class UserCreate(UserBase):
    """Wird genutzt, wenn HR einen neuen Mitarbeiter anlegt (inkl. Passwort)."""
    password: str = Field(..., min_length=6, description="Das Initialpasswort (mind. 6 Zeichen)")


class UserResponse(UserBase):
    """Wird genutzt, wenn wir User-Daten über die API zurückgeben (OHNE Passwort!)."""
    id: int
    progress_percent: int
    created_at: datetime

    # Diese Konfiguration sagt Pydantic, dass es Daten direkt aus einem 
    # SQLAlchemy-Datenbankobjekt lesen kann (orm_mode für Pydantic v2).
    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# 2. DOCUMENT-SCHEMAS
# -------------------------------------------------------------------------
class DocumentBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    category: str = Field(..., description="IT, Allgemein oder Projektname")


class DocumentCreate(DocumentBase):
    filepath: str


class DocumentResponse(DocumentBase):
    id: int
    filepath: str
    uploaded_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# 3. CHAT-NACHRICHTEN-SCHEMAS
# -------------------------------------------------------------------------
class ChatMessageCreate(BaseModel):
    user_id: int
    user_question: str


class ChatMessageResponse(BaseModel):
    id: int
    user_id: int
    user_question: str
    ai_response: str
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# 4. TASK-SCHEMAS
# -------------------------------------------------------------------------
class TaskBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    task_type: str = Field(..., description="Entweder 'Onboarding' oder 'Projekt'")
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
# SCHRITT 3: DIE DATENBANK-SESSION ALS ABHÄNGIGKEIT & ERSTER TEST-ENDPOINT
# =========================================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def check_connection(db: Session = Depends(get_db)):
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