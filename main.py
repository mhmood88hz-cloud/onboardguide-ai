# =========================================================================
# SCHRITT 1: DIE IMPORTE (UNSERE WERKZEUGKISTE)
# =========================================================================

import os
import shutil
from datetime import datetime, timezone
from typing import Optional, List, Literal
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File, Form, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import create_engine, text, Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, declarative_base, relationship
from dotenv import load_dotenv
from passlib.context import CryptContext
from openai import OpenAI


# =========================================================================
# SCHRITT 2: KONFIGURATION & INITIALISIERUNG (UNSER FUNDAMENT)
# =========================================================================

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_TOKEN  = os.getenv("ADMIN_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Maximale Anzahl geladener Chat-Nachrichten pro Anfrage (kein Magic-Number im Code)
CHAT_HISTORY_LIMIT = 5

# Lokaler Ordner für hochgeladene Dokumente
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

engine       = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()

app = FastAPI(
    title="OnboardGuide AI Backend",
    description=(
        "Intelligentes HR-Einarbeitungsportal mit RAG, History, "
        "Structured Outputs, Dokument-Upload und rollenbasierter Zugriffskontrolle."
    ),
    version="1.3.0"
)

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# =========================================================================
# SCHRITT 3: DATENBANK-MODELLE (POSTGRES-TABELLEN ALS PYTHON-KLASSEN)
# =========================================================================

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(100), unique=True, nullable=False)
    email           = Column(String(100), unique=True, nullable=False)
    password_hash   = Column(String(60),  nullable=False)
    user_role       = Column(String(20),  nullable=False)   # 'Verwaltung' | 'Leader' | 'Mitarbeiter'
    assigned_project= Column(String(100), nullable=True)
    department      = Column(String(100), nullable=True)
    reports_to      = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    progress_percent= Column(Integer, default=0)
    created_at      = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    documents    = relationship("Document",    back_populates="uploader")
    chat_messages= relationship("ChatMessage", back_populates="user")
    tasks_assigned = relationship("Task", foreign_keys="Task.assigned_to", back_populates="assignee")
    tasks_created  = relationship("Task", foreign_keys="Task.assigned_by", back_populates="creator")


class Document(Base):
    __tablename__ = "documents"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(255), nullable=False)
    filepath    = Column(String(512), nullable=False)   # Pfad zur Originaldatei (für Download)
    # -------------------------------------------------------------------------
    # KORREKTUR #3 – NEU: content-Spalte
    # Speichert den extrahierten Rohtext der Datei.
    # Nur so kann das Sprachmodell echten Dokumenteninhalt als RAG-Kontext erhalten.
    # filepath bleibt erhalten für Downloads; content wird für die KI genutzt.
    # -------------------------------------------------------------------------
    content     = Column(Text, nullable=True)
    category    = Column(String(100), nullable=False)   # 'Allgemein' | Abteilung | Projektname
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    uploader = relationship("User", back_populates="documents")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_question = Column(Text, nullable=False)
    ai_response   = Column(Text, nullable=False)
    created_at    = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    user = relationship("User", back_populates="chat_messages")


class Task(Base):
    __tablename__ = "tasks"

    id           = Column(Integer, primary_key=True, index=True)
    title        = Column(String(255), nullable=False)
    description  = Column(Text, nullable=True)
    task_type    = Column(String(20),  nullable=False)   # 'Onboarding' | 'Projekt'
    project_name = Column(String(100), nullable=True)
    assigned_to  = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),  nullable=False)
    assigned_by  = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="tasks_assigned")
    creator  = relationship("User", foreign_keys=[assigned_by], back_populates="tasks_created")


# =========================================================================
# SCHRITT 4: PYDANTIC-SCHEMAS (API-GATEKEEPER)
# =========================================================================

# ── User ──────────────────────────────────────────────────────────────────
class UserBase(BaseModel):
    username:         str = Field(..., min_length=3, max_length=100)
    email:            EmailStr
    user_role:        Literal["Verwaltung", "Leader", "Mitarbeiter"]
    assigned_project: Optional[str] = None
    department:       Optional[str] = None
    reports_to:       Optional[int] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id:               int
    progress_percent: int
    created_at:       datetime
    class Config:
        from_attributes = True

# ── Task ──────────────────────────────────────────────────────────────────
class TaskBase(BaseModel):
    title:        str = Field(..., min_length=3, max_length=255)
    description:  Optional[str] = None
    task_type:    Literal["Onboarding", "Projekt"]
    project_name: Optional[str] = None
    assigned_to:  int

class TaskCreate(TaskBase):
    assigned_by: Optional[int] = None

class TaskResponse(TaskBase):
    id:           int
    assigned_by:  Optional[int]
    is_completed: bool
    completed_at: Optional[datetime]
    created_at:   datetime
    class Config:
        from_attributes = True

# ── Leader ────────────────────────────────────────────────────────────────
class TeamMemberProgress(BaseModel):
    id:               int
    username:         str
    email:            str
    progress_percent: int
    department:       Optional[str] = None
    assigned_project: Optional[str] = None
    class Config:
        from_attributes = True

# ── Dokument ──────────────────────────────────────────────────────────────
class DocumentResponse(BaseModel):
    id:          int
    title:       str
    category:    str
    filepath:    str
    uploaded_by: Optional[int]
    created_at:  datetime
    # content wird NICHT zurückgegeben – zu groß für Listen-Responses
    class Config:
        from_attributes = True

# ── KI / Chat ─────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, description="Frage des Mitarbeiters an das System")

class ChatResponse(BaseModel):
    user_question:  str
    ai_response:    str
    used_documents: List[str] = Field(..., description="Quellennachweis der verwendeten Dokumente")

# Structured Output Schema – zwingt das LLM zu exaktem JSON-Format
class TaskExplanationLLMResponse(BaseModel):
    summary:       str       = Field(..., description="Kurze Zusammenfassung der Aufgabe")
    steps:         List[str] = Field(..., description="Schritt-für-Schritt-Anleitung")
    tools_and_tips:List[str] = Field(..., description="Hilfreiche Tools oder Insider-Tipps")

# Wrapper für den explain-Endpoint (KORREKTUR #2: response_model benötigt festes Schema)
class TaskExplainEndpointResponse(BaseModel):
    task_id:     int
    task_title:  str
    explanation: TaskExplanationLLMResponse


# =========================================================================
# SCHRITT 5: DEPENDENCIES & HILFSFUNKTIONEN
# =========================================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def verify_admin_token(
    x_admin_token: str = Header(..., description="Geheimer Admin-Token für administrative Aktionen")
):
    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="Server-Konfigurationsfehler: ADMIN_TOKEN nicht in .env!"
        )
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Ungültiger Admin-Token!")
    return x_admin_token


# -------------------------------------------------------------------------
# KORREKTUR #1 – get_current_user gibt nur die ID zurück
#
# Vorher: get_current_user öffnete eine eigene DB-Session via Depends(get_db).
# Das führte zu zwei parallelen Sessions pro Request (eine im Endpoint,
# eine in get_current_user). FastAPI cached Depends() zwar innerhalb eines
# Requests, aber nur wenn der Depends-Pfad identisch ist – das ist
# fragiles Verhalten. Sauberer: Header-Extraktion und DB-Zugriff trennen.
# Der Endpoint lädt den User dann mit seiner eigenen (einzigen) Session.
# -------------------------------------------------------------------------
def get_current_user(
    x_user_id: int = Header(..., description="Die ID des aktuell angemeldeten Benutzers")
) -> int:
    """Extrahiert die User-ID aus dem Request-Header. Kein eigener DB-Zugriff."""
    return x_user_id


def _load_current_user(user_id: int, db: Session) -> User:
    """
    Lädt den User aus der DB. Wird in Endpoints aufgerufen, die bereits
    eine Session besitzen – so bleibt es bei einer einzigen Session pro Request.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige x-user-id! Benutzer nicht gefunden."
        )
    return user


def update_user_progress(db: Session, user_id: int):
    """Berechnet progress_percent vollautomatisch neu nach jeder Task-Änderung."""
    user_tasks = db.query(Task).filter(Task.assigned_to == user_id).all()
    if not user_tasks:
        new_progress = 0
    else:
        completed = sum(1 for t in user_tasks if t.is_completed)
        new_progress = int((completed / len(user_tasks)) * 100)

    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.progress_percent = new_progress
        db.commit()
        db.refresh(db_user)


# =========================================================================
# SCHRITT 6: CRUD-ENDPOINTS
# =========================================================================

@app.get("/")
def check_connection(db: Session = Depends(get_db)):
    """Verbindungstest – prüft DB und OpenAI-Status."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status":        "online",
            "database":      "onboardguide_db",
            "openai_client": "Aktiv" if openai_client else "Inaktiv (kein API-Key)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB-Verbindung fehlgeschlagen: {str(e)}")


# ── USER: Registrieren ────────────────────────────────────────────────────
@app.post(
    "/api/auth/register",
    response_model=UserResponse,
    status_code=201,
    dependencies=[Depends(verify_admin_token)]
)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Neuen Benutzer anlegen. Nur mit gültigem Admin-Token."""
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Benutzername bereits registriert!")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert!")

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
    return new_user


# ── USER: Löschen ─────────────────────────────────────────────────────────
@app.delete("/api/users/{user_id}", status_code=200, dependencies=[Depends(verify_admin_token)])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    Löscht einen Benutzer. Cascade-Verhalten:
    • tasks.assigned_to   → CASCADE  (verwaiste Tasks gelöscht)
    • tasks.assigned_by   → SET NULL (Task bleibt, Ersteller-Verweis = NULL)
    • documents.uploaded_by → SET NULL (Dokumente bleiben erhalten!)
    • chat_messages       → CASCADE  (Chatverläufe bereinigt)
    • users.reports_to    → SET NULL (Team-Mitglieder bleiben)
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden!")

    info = {
        "deleted_user_id": db_user.id,
        "deleted_username": db_user.username,
        "deleted_email":    db_user.email,
        "deleted_role":     db_user.user_role,
    }

    # FIX: synchronize_session="fetch" delegiert die Cascade-Logik direkt an
    # PostgreSQL statt sie über Python-Relationships abzuwickeln.
    # db.delete(db_user) versuchte assigned_to auf NULL zu setzen →
    # NOT NULL Constraint Fehler. Diese Variante lässt PostgreSQL CASCADE
    # sauber ausführen wie in der DB-Constraint definiert.
    db.query(User).filter(User.id == user_id).delete(synchronize_session="fetch")
    db.commit()
    return {"status": "success", "message": f"Benutzer '{info['deleted_username']}' gelöscht.", **info}


# ── TASK: Erstellen ───────────────────────────────────────────────────────
@app.post("/api/tasks", response_model=TaskResponse, status_code=201)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    if not db.query(User).filter(User.id == task.assigned_to).first():
        raise HTTPException(status_code=404, detail="Mitarbeiter (assigned_to) nicht gefunden!")

    new_task = Task(**task.model_dump())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    update_user_progress(db, task.assigned_to)
    db.refresh(new_task)
    return new_task


# ── TASK: Abrufen ─────────────────────────────────────────────────────────
@app.get("/api/tasks", response_model=List[TaskResponse])
def get_user_tasks(user_id: int, db: Session = Depends(get_db)):
    if not db.query(User).filter(User.id == user_id).first():
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden!")
    return db.query(Task).filter(Task.assigned_to == user_id).all()


# ── TASK: Als erledigt markieren (mit Berechtigungsprüfung) ───────────────
@app.put("/api/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id:     int,
    db:          Session = Depends(get_db),
    user_id:     int     = Depends(get_current_user)   # KORREKTUR #1: nur ID
):
    """
    Markiert eine Aufgabe als erledigt.

    Berechtigungsformel:
    Zulässig ⟺  (U_id = T_assigned_to)
              ∨  (U_role = 'Verwaltung')
              ∨  (U_role = 'Leader' ∧ T_assigned_to ∈ ReportsOf(U_id))
    """
    # User mit der einzigen vorhandenen Session laden
    current_user = _load_current_user(user_id, db)

    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden!")

    assignee = db.query(User).filter(User.id == db_task.assigned_to).first()

    is_assigned_user  = (current_user.id == db_task.assigned_to)
    is_hr             = (current_user.user_role == "Verwaltung")
    is_direct_leader  = (
        assignee is not None
        and assignee.reports_to == current_user.id
        and current_user.user_role == "Leader"
    )

    if not (is_assigned_user or is_hr or is_direct_leader):
        raise HTTPException(
            status_code=403,
            detail=(
                "Nicht berechtigt! Nur der zugewiesene Mitarbeiter, "
                "ein HR-Administrator oder der direkte Teamleiter dürfen diese Aufgabe abschließen."
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


# ── LEADER: Team-Fortschritt ───────────────────────────────────────────────
@app.get("/api/leader/progress", response_model=List[TeamMemberProgress])
def get_leader_team_progress(leader_id: int, db: Session = Depends(get_db)):
    leader = db.query(User).filter(User.id == leader_id, User.user_role == "Leader").first()
    if not leader:
        raise HTTPException(status_code=404, detail="Teamleiter nicht gefunden!")
    return db.query(User).filter(User.reports_to == leader_id).all()


# =========================================================================
# SCHRITT 7: DOKUMENT-VERWALTUNG (UPLOAD + ROLLENBASIERTER ZUGRIFF)
# =========================================================================

# -------------------------------------------------------------------------
# KORREKTUR #3 – Dokument-Upload mit Content-Extraktion und RAG-Vorbereitung
#
# Problem vorher: Die 'documents'-Tabelle speicherte nur den filepath.
# Das Sprachmodell bekam also "/uploads/datei.pdf" als RAG-Kontext –
# völlig wertlos. Ein Modell kann keinen Pfad lesen, es braucht echten Text.
#
# Lösung: Beim Upload wird der Dateiinhalt (Text) in der neuen 'content'-
# Spalte gespeichert. Der RAG-Endpoint liest dann doc.content statt doc.filepath.
# filepath bleibt für Downloads erhalten.
#
# Berechtigungsmodell für Dokumente:
#   category = 'Allgemein'   → alle Mitarbeiter, Leader, Verwaltung
#   category = 'IT'          → nur IT-Mitarbeiter + Leader + Verwaltung
#   category = 'Alpha-Projekt' → nur Mitarbeiter mit assigned_project='Alpha-Projekt'
#                                + Leader + Verwaltung
#
# Der Upload selbst ist auf Verwaltung/Leader beschränkt (Admin-Token).
# -------------------------------------------------------------------------

@app.post(
    "/api/documents/upload",
    response_model=DocumentResponse,
    status_code=201,
    dependencies=[Depends(verify_admin_token)]
)
async def upload_document(
    title:       str        = Form(..., description="Titel des Dokuments"),
    category:    str        = Form(..., description="'Allgemein', Abteilungsname oder Projektname"),
    uploaded_by: int        = Form(..., description="User-ID des Uploaders"),
    file:        UploadFile = File(..., description="Textdatei (.txt) oder PDF"),
    db:          Session    = Depends(get_db)
):
    """
    Lädt ein Dokument hoch, speichert die Datei lokal und extrahiert den
    Textinhalt in die 'content'-Spalte für die RAG-Pipeline.

    Unterstützte Formate: .txt (direkt lesbar), .pdf (Rohtext-Extraktion).
    category bestimmt, welche Benutzergruppe das Dokument im Chat sieht.
    """
    # Datei lokal speichern
    safe_filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path     = UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Textinhalt extrahieren – je nach Dateiformat
    content_text = None
    suffix       = Path(file.filename).suffix.lower()

    if suffix == ".txt":
        # .txt direkt lesen
        content_text = file_path.read_text(encoding="utf-8", errors="ignore")

    elif suffix == ".pdf":
        # PDF-Text-Extraktion via pypdf (pip install pypdf)
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            pages  = [page.extract_text() or "" for page in reader.pages]
            content_text = "\n".join(pages).strip() or None
        except ImportError:
            # pypdf nicht installiert → Inhalt bleibt NULL
            # RAG-Fallback: Titel + Kategorie als Kontext-Signal (siehe Endpoint unten)
            content_text = None

    else:
        # Unbekanntes Format → Datei bleibt, content = NULL
        content_text = None

    new_doc = Document(
        title=title,
        filepath=str(file_path),
        content=content_text,
        category=category,
        uploaded_by=uploaded_by
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    return new_doc


@app.get("/api/documents", response_model=List[DocumentResponse])
def get_documents(
    db:      Session = Depends(get_db),
    user_id: int     = Depends(get_current_user)
):
    """
    Gibt alle Dokumente zurück, die der anfragende User sehen darf.

    Berechtigungslogik:
    • Verwaltung → alle Dokumente
    • Leader     → Allgemein + eigene Abteilung + Projekte seiner Teammitglieder
    • Mitarbeiter→ Allgemein + eigene Abteilung + eigenes Projekt
    """
    current_user = _load_current_user(user_id, db)

    if current_user.user_role == "Verwaltung":
        return db.query(Document).all()

    allowed_categories = {"Allgemein"}

    if current_user.user_role == "Leader":
        # Leader sieht die Kategorien aller ihm unterstellten Mitarbeiter
        team = db.query(User).filter(User.reports_to == current_user.id).all()
        for member in team:
            if member.department:
                allowed_categories.add(member.department)
            if member.assigned_project:
                allowed_categories.add(member.assigned_project)

    else:  # Mitarbeiter
        if current_user.department:
            allowed_categories.add(current_user.department)
        if current_user.assigned_project:
            allowed_categories.add(current_user.assigned_project)

    return db.query(Document).filter(Document.category.in_(allowed_categories)).all()


# =========================================================================
# SCHRITT 8: PROMPT ENGINEERING & KI-INTEGRATION (OPENAI SDK)
# =========================================================================

# ── KI-Endpoint 1: RAG-Chatbot (Säulen A + B + C) ────────────────────────
@app.post("/api/chat/ask", response_model=ChatResponse)
def ask_onboarding_guide(
    request: ChatRequest,
    db:      Session = Depends(get_db),
    user_id: int     = Depends(get_current_user)
):
    """
    Onboarding-Chatbot mit drei Prompt-Engineering-Säulen:
    • Säule A: Conversation History  – letzte k Nachrichten aus chat_messages
    • Säule B: Dynamic Context Injection – System-Prompt nach Rolle/Abteilung/Projekt
    • Säule C: RAG – Dokumenteninhalt (doc.content) als einzige Quelle der Wahrheit
    """
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI-Client nicht aktiv!")

    current_user = _load_current_user(user_id, db)

    # ── SÄULE B: Dynamic Context Injection ───────────────────────────────
    system_prompt = (
        f"Du bist der persönliche Onboarding-Assistent für {current_user.username}. "
        f"Abteilung: '{current_user.department or 'Allgemein'}', "
        f"Projekt: '{current_user.assigned_project or 'Keines'}', "
        f"Rolle: '{current_user.user_role}'. "
        "Antworte AUSSCHLIESSLICH auf Basis der bereitgestellten Firmendokumente. "
        "Wenn die Antwort nicht in den Dokumenten steht, sage das ehrlich."
    )

    # ── SÄULE C: RAG – Dokumente filtern und echten Content laden ────────
    # Berechtigungsformel:
    # D_relevant = { d | d.category ∈ {'Allgemein', U_department, U_assigned_project} }
    categories = {"Allgemein"}
    if current_user.department:
        categories.add(current_user.department)
    if current_user.assigned_project:
        categories.add(current_user.assigned_project)

    documents = db.query(Document).filter(Document.category.in_(categories)).all()

    context_text  = ""
    context_titles = []

    if documents:
        context_text = "=== FIRMENDOKUMENTE (einzige Quelle der Wahrheit) ===\n\n"
        for doc in documents:
            context_titles.append(doc.title)
            # KORREKTUR #3: doc.content statt doc.filepath
            if doc.content:
                # Echter Dokumenteninhalt vorhanden → für RAG nutzen
                preview = doc.content[:2000]  # Max. 2000 Zeichen pro Dokument
                context_text += f"--- {doc.title} (Kategorie: {doc.category}) ---\n{preview}\n\n"
            else:
                # Kein Inhalt extrahierbar (z.B. Bild-PDF) → Fallback: Metadaten
                context_text += f"--- {doc.title} (Kategorie: {doc.category}) ---\n[Inhalt nicht extrahierbar]\n\n"
    else:
        context_text = "Es wurden keine Dokumente für dein Profil gefunden. Antworte allgemein."

    # ── SÄULE A: Conversation History ────────────────────────────────────
    messages_payload = [{"role": "system", "content": system_prompt}]

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(CHAT_HISTORY_LIMIT)
        .all()
    )
    for msg in reversed(history):  # Chronologisch: älteste zuerst
        messages_payload.append({"role": "user",      "content": msg.user_question})
        messages_payload.append({"role": "assistant",  "content": msg.ai_response})

    # Aktuelle Frage + RAG-Kontext zusammenführen
    messages_payload.append({
        "role":    "user",
        "content": f"{context_text}\n\nFrage: {request.question}"
    })

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages_payload,
            temperature=0.4
        )
        ai_reply = response.choices[0].message.content

        # Verlauf für nächste Sitzung persistieren
        db.add(ChatMessage(
            user_id=current_user.id,
            user_question=request.question,
            ai_response=ai_reply
        ))
        db.commit()

        return ChatResponse(
            user_question=request.question,
            ai_response=ai_reply,
            used_documents=context_titles
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI-Fehler: {str(e)}")


# ── KI-Endpoint 2: Task-Erklärer mit Structured Outputs ──────────────────
@app.post(
    "/api/chat/tasks/{task_id}/explain",
    response_model=TaskExplainEndpointResponse   # KORREKTUR #2: festes response_model
)
def explain_task_personalized(
    task_id: int,
    db:      Session = Depends(get_db),
    user_id: int     = Depends(get_current_user)
):
    """
    Erklärt eine Aufgabe Schritt für Schritt – personalisiert auf Rolle,
    Abteilung und Projekt. Nutzt OpenAI Structured Outputs (.parse),
    um garantiert valides JSON im Format TaskExplanationLLMResponse zu erhalten.
    """
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI-Client nicht aktiv!")

    current_user = _load_current_user(user_id, db)

    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden!")

    if db_task.assigned_to != current_user.id and current_user.user_role == "Mitarbeiter":
        raise HTTPException(status_code=403, detail="Du kannst nur deine eigenen Aufgaben erklären lassen!")

    system_prompt = (
        "Du bist ein erfahrener technischer Onboarding-Coach. "
        f"Erkläre dem Mitarbeiter '{current_user.username}' "
        f"(Rolle: {current_user.user_role}, "
        f"Abteilung: {current_user.department or 'Allgemein'}, "
        f"Projekt: {current_user.assigned_project or 'Keines'}) "
        "die folgende Aufgabe Schritt für Schritt. "
        "Passe Fachbegriffe, Tiefe und Beispiele exakt an sein Profil an. "
        "Antworte AUSSCHLIESSLICH im vorgegebenen JSON-Format."
    )

    prompt_content = (
        f"Aufgabe: {db_task.title}\n"
        f"Beschreibung: {db_task.description or 'Keine Beschreibung'}\n"
        f"Typ: {db_task.task_type}\n"
        f"Projekt: {db_task.project_name or 'Keines'}"
    )

    try:
        # Structured Outputs: .parse erzwingt das Pydantic-Schema als JSON
        response = openai_client.beta.chat.completions.parse(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": prompt_content}
            ],
            response_format=TaskExplanationLLMResponse,
            temperature=0.4
        )
        parsed = response.choices[0].message.parsed

        # KORREKTUR #2: Rückgabe als typisiertes Pydantic-Objekt statt rohem Dict
        return TaskExplainEndpointResponse(
            task_id=task_id,
            task_title=db_task.title,
            explanation=parsed
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI Structured Output Fehler: {str(e)}"
        )