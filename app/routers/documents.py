import json
import re
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
from app.services.chunking_service import embed_document

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
    if not db.query(User).filter(User.id == uploaded_by).first():
        raise HTTPException(status_code=404, detail="Uploader nicht gefunden!")

    start_trace()
    log_step("User", "Main",
             "POST /api/documents/upload",
             f"Admin lädt Dokument '{title}' hoch (Kategorie: {category}).")
    log_step("Main", "Security",
             "Admin-Token Prüfung",
             "verify_admin_token prüft den x-admin-token Header.")
    log_step("Security", "Router",
             "Berechtigung bestätigt",
             "Token gültig – Anfrage wird an routers/documents.py weitergeleitet.")
    log_step("Router", "Schema",
             "Datei in Speicher einlesen",
             "await file.read() liest alle Bytes auf einmal. "
             "Verhindert Stream-Exhaustion bei pypdf.")

    file_bytes = await file.read()

    original_filename = Path(file.filename or "upload").name
    safe_original = re.sub(r"[^A-Za-z0-9._-]", "_", original_filename).strip("._")
    safe_filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{safe_original or 'upload'}"
    file_path     = UPLOAD_DIR / safe_filename
    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    log_step("Router", "Database",
             "Datei auf Disk gespeichert",
             f"Datei wurde lokal als '{safe_filename}' im uploads/-Ordner gesichert.")

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

    extracted = f"{len(content_text)} Zeichen extrahiert." if content_text else "Kein Text extrahiert."
    log_step("Router", "AIService",
             "Text-Extraktion (RAG Vorbereitung)",
             f"pypdf verarbeitet '{suffix}'-Datei. {extracted} "
             "content-Spalte speichert den Rohtext für die RAG-Pipeline.")

    new_doc = Document(
        title=title, filepath=str(file_path),
        content=content_text, category=category, uploaded_by=uploaded_by
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    log_step("AIService", "PostgreSQL",
             "Dokument in DB gespeichert",
             f"Neuer Eintrag in documents-Tabelle. "
             f"id={new_doc.id}, Kategorie='{category}', "
             f"Inhalt={'gesetzt' if content_text else 'NULL'}.")

    chunk_stats = {"chunks_created": 0}
    if content_text:
        log_step("PostgreSQL", "AIService",
                 "Chunking + Einbettung gestartet",
                 "Text wird in Chunks aufgeteilt und Einbettungen via "
                 "text-embedding-3-small erstellt.")
        try:
            chunk_stats = embed_document(new_doc.id, content_text, db)
            log_step("AIService", "PostgreSQL",
                     "Chunks gespeichert",
                     f"{chunk_stats['chunks_created']} Chunks eingebettet und in "
                     f"document_chunks gespeichert "
                     f"({chunk_stats.get('elapsed_seconds', '?')}s).")
        except Exception as e:
            log_step("AIService", "PostgreSQL",
                     "Einbettung fehlgeschlagen",
                     f"Fehler: {str(e)} – Dokument ohne Chunks gespeichert.")

    log_step("PostgreSQL", "Schema",
             "Response-Validierung",
             "Pydantic DocumentResponse: content-Feld wird weggelassen (zu groß).")
    log_step("Schema", "User",
             "201 Erstellt",
             f"Admin erhält Dokumentdaten. {chunk_stats['chunks_created']} Chunks erstellt.")

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
    """Rollenbasierter Dokumentenzugriff."""
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
