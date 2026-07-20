import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Document
from app.schemas import DocumentResponse
from app.security import verify_admin_token, get_current_user, load_current_user
from app.services.trace import start_trace, log_step, get_trace
from app.services.ws_manager import manager
from app.services.chunking_service import embed_document   # NEW

router    = APIRouter(prefix="/api/documents", tags=["Documents"])
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload", response_model=DocumentResponse, status_code=201,
             dependencies=[Depends(verify_admin_token)])
async def upload_document(
    response:    Response,
    title:       str        = Form(...),
    category:    str        = Form(...),
    uploaded_by: int        = Form(...),
    file:        UploadFile = File(...),
    db:          Session    = Depends(get_db)
):
    start_trace()
    log_step("User", "Main",
             "POST /api/documents/upload",
             f"Admin uploads '{title}' (category: {category}).")
    log_step("Main", "Security",
             "Admin-Token Check",
             "verify_admin_token validates x-admin-token header.")
    log_step("Security", "Router",
             "Authorized",
             "Token valid – request continues to routers/documents.py.")
    log_step("Router", "Schema",
             "File read into memory",
             "await file.read() reads all bytes at once.")

    # ── Read file ─────────────────────────────────────────────────────
    file_bytes = await file.read()

    # ── Save to disk ──────────────────────────────────────────────────
    safe_filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path     = UPLOAD_DIR / safe_filename
    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    log_step("Router", "Database",
             "File saved to disk",
             f"Stored as '{safe_filename}' in uploads/ folder.")

    # ── Extract text ──────────────────────────────────────────────────
    content_text = None
    suffix       = Path(file.filename).suffix.lower()

    if suffix == ".txt":
        content_text = file_bytes.decode("utf-8", errors="ignore").strip() or None
    elif suffix == ".pdf":
        try:
            import io
            from pypdf import PdfReader
            reader       = PdfReader(io.BytesIO(file_bytes))
            content_text = "\n".join(
                p.extract_text() or "" for p in reader.pages
            ).strip() or None
        except Exception:
            content_text = None

    extracted = f"{len(content_text)} chars extracted." if content_text else "No text extracted."
    log_step("Router", "AIService",
             "Text extraction",
             f"pypdf ran on '{suffix}' file. {extracted}")

    # ── Save document to DB ───────────────────────────────────────────
    new_doc = Document(
        title=title, filepath=str(file_path),
        content=content_text, category=category, uploaded_by=uploaded_by
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    log_step("AIService", "PostgreSQL",
             "Document saved",
             f"New row in documents table. id={new_doc.id}.")

    # ── Chunking + Embedding (NEW) ────────────────────────────────────
    chunk_stats = {"chunks_created": 0}

    if content_text:
        log_step("PostgreSQL", "AIService",
                 "Chunking + Embedding started",
                 f"Splitting text into chunks and creating embeddings via "
                 f"text-embedding-3-small.")
        try:
            chunk_stats = embed_document(new_doc.id, content_text, db)
            log_step("AIService", "PostgreSQL",
                     "Chunks saved",
                     f"{chunk_stats['chunks_created']} chunks embedded and saved "
                     f"to document_chunks in {chunk_stats.get('elapsed_seconds', '?')}s.")
        except Exception as e:
            log_step("AIService", "PostgreSQL",
                     "Embedding failed",
                     f"Error: {str(e)} – document saved without chunks.")

    log_step("PostgreSQL", "Schema",
             "Response validation",
             "Pydantic DocumentResponse excludes content field.")
    log_step("Schema", "User",
             "201 Created",
             f"Document saved. {chunk_stats['chunks_created']} chunks created. "
             f"Simulator received full trace.")

    # ── Broadcast trace ───────────────────────────────────────────────
    await manager.broadcast_trace(
        get_trace(), f"POST /api/documents/upload ({title})"
    )
    response.headers["X-Workflow-Trace"] = json.dumps(get_trace())

    return new_doc


@router.get("", response_model=List[DocumentResponse])
def get_documents(
    db:      Session = Depends(get_db),
    user_id: int     = Depends(get_current_user)
):
    """Role-based document access filter."""
    current_user = load_current_user(user_id, db)
    if current_user.user_role == "Verwaltung":
        return db.query(Document).all()
    allowed = {"Allgemein"}
    if current_user.user_role == "Leader":
        for m in db.query(User).filter(User.reports_to == current_user.id).all():
            if m.department:       allowed.add(m.department)
            if m.assigned_project: allowed.add(m.assigned_project)
    else:
        if current_user.department:       allowed.add(current_user.department)
        if current_user.assigned_project: allowed.add(current_user.assigned_project)
    return db.query(Document).filter(Document.category.in_(allowed)).all()