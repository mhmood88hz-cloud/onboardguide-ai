import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, text, Column, Integer, String, Boolean, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, declarative_base, relationship

from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Sessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
app = FastAPI(title="OnboardGuide AI Backend")
# 1. DAS USER-MODELL (Tabelle: users)
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
    id = Column(Integer, primary_key= True, index = True)
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

def get_db():# -> Session:
    db = Sessionlocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def check_connection(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "online",
                "message": "Database connection successful",
                "database": "OnboardGuide AI"
                }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed {str(e)}"
        )

