from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy import text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    username         = Column(String(100), unique=True, nullable=False)
    email            = Column(String(100), unique=True, nullable=False)
    password_hash    = Column(String(60),  nullable=False)
    user_role        = Column(String(20),  nullable=False)  # 'Verwaltung' | 'Leader' | 'Mitarbeiter'
    assigned_project = Column(String(100), nullable=True)
    department       = Column(String(100), nullable=True)
    reports_to       = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    progress_percent = Column(Integer, default=0)
    created_at       = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    documents      = relationship("Document",    back_populates="uploader")
    chat_messages  = relationship("ChatMessage", back_populates="user")
    tasks_assigned = relationship("Task", foreign_keys="Task.assigned_to", back_populates="assignee")
    tasks_created  = relationship("Task", foreign_keys="Task.assigned_by", back_populates="creator")


class Document(Base):
    __tablename__ = "documents"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(255), nullable=False)
    filepath    = Column(String(512), nullable=False)
    content     = Column(Text, nullable=True)              # extracted text for RAG
    category    = Column(String(100), nullable=False)      # 'Allgemein' | department | project
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    uploader = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document",
                          cascade="all, delete-orphan")

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
    task_type    = Column(String(20),  nullable=False)  # 'Onboarding' | 'Projekt'
    project_name = Column(String(100), nullable=True)
    assigned_to  = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),  nullable=False)
    assigned_by  = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="tasks_assigned")
    creator  = relationship("User", foreign_keys=[assigned_by], back_populates="tasks_created")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id          = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)    # position in document
    content     = Column(Text, nullable=False)       # chunk text
    embedding   = Column(Vector(1536), nullable=True) # pgvector column
    token_count = Column(Integer, nullable=True)     # number of tokens
    chunk_metadata = Column(JSONB, nullable=True)
    created_at  = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    document = relationship("Document", back_populates="chunks")
