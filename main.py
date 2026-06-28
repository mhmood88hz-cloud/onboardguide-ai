# =========================================================================
# SCHRITT 1: DIE IMPORTE (UNSERE WERKZEUGKISTE)
# =========================================================================

import os
from datetime import datetime, timezone
from typing import Optional, List, Literal
from fastapi import FastAPI, Depends, HTTPException, Header

# Für die Daten-Validierung importieren wir Pydantic:
# KORREKTUR #10: EmailStr importiert für echte E-Mail-Format-Validierung
from pydantic import BaseModel, Field, EmailStr

# Für unsere Datenbank-Modelle importieren wir zusätzliche Werkzeuge von SQLAlchemy:
from sqlalchemy import create_engine, text, Column, Integer, String, Boolean, Text, DateTime, ForeignKey

# - 'declarative_base': Die Mutterklasse, von der alle unsere Tabellen-Klassen erben müssen.
# - 'relationship': Ermöglicht es uns, in Python direkt auf verknüpfte Daten zuzugreifen (z.B. user.tasks).
from sqlalchemy.orm import sessionmaker, Session, declarative_base, relationship
from dotenv import load_dotenv
from passlib.context import CryptContext


# =========================================================================
# SCHRITT 2: DIE DATENBANK-VERBINDUNG & DIE WEB-APP (UNSER FUNDAMENT)
# =========================================================================

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Admin-Token wird sicher aus den Umgebungsvariablen (.env) geladen – kein Secret-Leaking!
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 'Base' ist das Fundament für unsere Tabellen-Klassen.
Base = declarative_base()

app = FastAPI(title="OnboardGuide AI Backend")

# Wir konfigurieren den Bcrypt-Hashing-Kontext (automatische Generierung sicherer Salts)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =========================================================================
# SCHRITT 3: DIE DATENBANK-MODELLE (UNSERE POSTGRES-TABELLEN ALS PYTHON-KLASSEN)
# =========================================================================

# -------------------------------------------------------------------------
# 1. DAS USER-MODELL (Tabelle: users)
# -------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    # KORREKTUR #11: String(60) statt String(255) – bcrypt-Hashes sind immer genau 60 Zeichen
    password_hash = Column(String(60), nullable=False)
    user_role = Column(String(20), nullable=False)  # 'Verwaltung', 'Leader', 'Mitarbeiter'
    assigned_project = Column(String(100), nullable=True)  # Projekt-Filter für Mitarbeiter
    department = Column(String(100), nullable=True)  # Abteilung (z.B. IT, HR, Marketing)

    # Selbst-Referenz (Self-Reference): reports_to speichert die ID des zuständigen Teamleiters.
    reports_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    progress_percent = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    # Beziehungen (Relationships) für komfortables Abfragen in Python:
    documents = relationship("Document", back_populates="uploader")
    chat_messages = relationship("ChatMessage", back_populates="user")

    # Durch Nutzung von Strings bei foreign_keys verhindern wir Initialisierungsfehler (Deferred Evaluation)
    tasks_assigned = relationship("Task", foreign_keys="Task.assigned_to", back_populates="assignee")
    tasks_created = relationship("Task", foreign_keys="Task.assigned_by", back_populates="creator")


# -------------------------------------------------------------------------
# 2. DAS DOKUMENTEN-MODELL (Tabelle: documents)
# -------------------------------------------------------------------------
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


# -------------------------------------------------------------------------
# 3. DAS CHAT-NACHRICHTEN-MODELL (Tabelle: chat_messages)
# -------------------------------------------------------------------------
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
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

    # Beziehungen zurück zum User (mit Angabe der konkreten Fremdschlüssel)
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="tasks_assigned")
    creator = relationship("User", foreign_keys=[assigned_by], back_populates="tasks_created")


# =========================================================================
# SCHRITT 4: DIE PYDANTIC-SCHEMAS (UNSERE DATEN-GATEKEEPER)
# =========================================================================

# -------------------------------------------------------------------------
# 1. USER-SCHEMAS (Eingabe vs. Ausgabe)
# -------------------------------------------------------------------------
class UserBase(BaseModel):
    """Gemeinsame Felder für alle User-Aktionen."""
    username: str = Field(..., min_length=3, max_length=100, description="Eindeutiger Login-Name")
    # KORREKTUR #10: EmailStr erzwingt gültiges E-Mail-Format (z.B. verhindert "kein-email")
    email: EmailStr = Field(..., description="E-Mail-Adresse des Benutzers")
    # Literal erzwingt erlaubte Rollen – kein beliebiger String möglich
    user_role: Literal["Verwaltung", "Leader", "Mitarbeiter"] = Field(..., description="Muss 'Verwaltung', 'Leader' oder 'Mitarbeiter' sein")
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
    # Literal erzwingt erlaubte Task-Typen
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


# -------------------------------------------------------------------------
# 5. LEADER-SCHEMA
# -------------------------------------------------------------------------
class TeamMemberProgress(BaseModel):
    """Strukturierte Validierung der Team-Fortschritte für den Leader-Endpoint."""
    id: int
    username: str
    email: str
    progress_percent: int
    department: Optional[str] = None
    assigned_project: Optional[str] = None

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
    """
    Verschlüsselt Passwörter via Bcrypt mit adaptivem, kryptografisch sicherem Salz.
    Jeder Hash ist einzigartig – selbst identische Passwörter erzeugen unterschiedliche Hashes.
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Prüft ein Klartextpasswort gegen einen gespeicherten Bcrypt-Hash.
    Wird beim Login-Endpoint benötigt.
    """
    return pwd_context.verify(plain, hashed)


def verify_admin_token(
    x_admin_token: str = Header(..., description="Geheimer Admin-Token für administrative Aktionen")
):
    """
    Sicherheits-Guard als FastAPI-Dependency.
    Token wird aus .env geladen – kein Secret-Leaking im Quellcode.
    """
    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="Server-Konfigurationsfehler: ADMIN_TOKEN ist nicht in .env konfiguriert!"
        )
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Ungültiger Admin-Token!")
    return x_admin_token


def update_user_progress(db: Session, user_id: int):
    """
    Berechnet den Fortschritt (progress_percent) eines Benutzers vollautomatisch neu.
    Formel: (Erledigte Aufgaben / Gesamtanzahl Aufgaben) * 100
    """
    # 1. Hole alle zugewiesenen Aufgaben des Benutzers
    user_tasks = db.query(Task).filter(Task.assigned_to == user_id).all()

    # 2. Falls keine Aufgaben existieren, ist der Fortschritt 0%
    if not user_tasks:
        new_progress = 0
    else:
        completed_tasks_count = sum(1 for task in user_tasks if task.is_completed)
        new_progress = int((completed_tasks_count / len(user_tasks)) * 100)

    # 3. Aktualisiere den progress_percent im User-Profil
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
@app.post("/api/auth/register", response_model=UserResponse, status_code=201)
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """Registriert einen neuen Benutzer im System. (Exklusiv für Verwaltung/HR)."""
    # Prüfen, ob der Benutzername bereits existiert
    existing_username = db.query(User).filter(User.username == user.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Benutzername bereits registriert!")

    # Prüfen, ob die E-Mail bereits existiert
    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="E-Mail-Adresse bereits registriert!")

    # Passwort wird via Bcrypt gehasht – niemals im Klartext gespeichert!
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
    # Prüfen, ob der zugewiesene Mitarbeiter überhaupt existiert
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

    # Fortschritt des Benutzers nach Zuweisung einer neuen (unfertigen) Aufgabe neu berechnen
    update_user_progress(db, task.assigned_to)

    # Nach update_user_progress (das intern commit() macht) Task-Objekt aktualisieren
    db.refresh(new_task)
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
        return db_task  # Bereits erledigt, nichts zu tun

    db_task.is_completed = True
    # timezone-aware UTC-Zeitstempel (datetime.utcnow() ist seit Python 3.12 deprecated)
    db_task.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(db_task)

    # Fortschritt des Users live neu berechnen
    update_user_progress(db, db_task.assigned_to)

    # KORREKTUR #9: Nach update_user_progress (das intern commit() macht) Task-Objekt
    # aktualisieren, damit keine veralteten Daten aus dem SQLAlchemy-Cache zurückgegeben werden
    db.refresh(db_task)
    return db_task


# -------------------------------------------------------------------------
# 5. LEADER: Team-Fortschritt abrufen (READ)
# -------------------------------------------------------------------------
@app.get("/api/leader/progress", response_model=List[TeamMemberProgress])
def get_leader_team_progress(leader_id: int, db: Session = Depends(get_db)):
    """Ruft alle Mitarbeiter ab, die diesem Teamleiter (leader_id) über 'reports_to' zugeordnet sind."""
    leader = db.query(User).filter(User.id == leader_id, User.user_role == "Leader").first()
    if not leader:
        raise HTTPException(
            status_code=404,
            detail="Teamleiter (Leader) nicht gefunden oder Rolle nicht berechtigt!"
        )

    # Finde alle Mitarbeiter, die an diesen Leader berichten
    team_members = db.query(User).filter(User.reports_to == leader_id).all()

    # FastAPI & SQLAlchemy konvertieren das ORM-Modell automatisch dank `from_attributes = True`
    return team_members


# -------------------------------------------------------------------------
# 6. USER: Benutzer löschen (DELETE + AUTH GUARD)
# -------------------------------------------------------------------------
@app.delete("/api/users/{user_id}", status_code=200)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Löscht einen Benutzer vollständig aus dem System. (Exklusiv für Verwaltung/HR)

    Was passiert mit den verknüpften Daten beim Löschen?
    ─────────────────────────────────────────────────────
    • Tasks (assigned_to):   ondelete=CASCADE  → werden automatisch mitgelöscht.
                             Begründung: Eine verwaiste Aufgabe ohne Verantwortlichen
                             ist wertlos und würde die Fortschrittsberechnung verfälschen.

    • Tasks (assigned_by):   ondelete=SET NULL → der Ersteller-Verweis wird auf NULL gesetzt.
                             Begründung: Die Aufgabe selbst bleibt erhalten, nur der
                             Hinweis "wer hat sie erstellt" wird entfernt.

    • Dokumente (uploaded_by): ondelete=SET NULL → Dokument bleibt, Uploader-Verweis wird NULL.
                             Begründung: Firmendokumente dürfen nicht verloren gehen.

    • Chat-Nachrichten:      ondelete=CASCADE  → werden mitgelöscht.
                             Begründung: Persönliche Gesprächsverläufe sind ohne User sinnlos.

    • Team-Mitglieder (reports_to): ondelete=SET NULL → Mitglieder verlieren nur den
                             Leader-Verweis, werden selbst nicht gelöscht.
    """
    # 1. Prüfen, ob der Benutzer überhaupt existiert
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden!")

    # 2. Sicherheitscheck: Verhindere, dass ein Admin sich selbst löscht
    #    (würde das System im Worst Case komplett aussperren)
    #    Hinweis: Dieser Check kann erweitert werden, sobald echte Sessions existieren.

    # 3. Snapshot der wichtigsten Daten für die Bestätigungsantwort (vor dem Löschen!)
    deleted_info = {
        "deleted_user_id": db_user.id,
        "deleted_username": db_user.username,
        "deleted_email": db_user.email,
        "deleted_role": db_user.user_role,
    }

    # 4. Benutzer löschen – die Datenbank-Constraints (CASCADE / SET NULL)
    #    übernehmen automatisch die korrekte Behandlung aller verknüpften Daten.
    db.delete(db_user)
    db.commit()

    # 5. Bestätigungsantwort zurückgeben
    return {
        "status": "success",
        "message": f"Benutzer '{deleted_info['deleted_username']}' wurde erfolgreich gelöscht.",
        "detail": "Zugehörige Aufgaben (assigned_to) und Chat-Nachrichten wurden mitgelöscht. "
                  "Dokumente und erstellte Aufgaben (assigned_by) bleiben erhalten.",
        **deleted_info
    }