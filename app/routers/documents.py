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
from app.services.ws_manager import manager   # WebSocket broadcast

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
    """
    Uploads a document and broadcasts the architectural trace
    to every connected MVC Simulator via WebSocket – automatically,
    without any manual action from the user.
    """

    # ── Record every layer transition ─────────────────────────────────
    start_trace()
    log_step("User",       "Main",
             "POST /api/documents/upload",
             f"Admin macht einen Request in Swagger: Dokument '{title}' hochladen (Kategorie: {category}).")
    log_step("Main",       "Security",
             "Admin-Token Guard",
             "dependencies=[Depends(verify_admin_token)] fängt den Request ab. x-admin-token Header wird geprüft.")
    log_step("Security",   "Router",
             "Berechtigung OK",
             "Token gültig – Request darf weiter zu routers/documents.py → upload_document().")
    log_step("Router",     "Schema",
             "Datei in Speicher lesen",
             f"await file.read() liest alle {'{size}'} Bytes auf einmal. Verhindert Stream-Exhaustion.")

    # Read file
    file_bytes = await file.read()

    # Update desc with real size
    trace = get_trace()
    trace[-1]["desc"] = trace[-1]["desc"].replace("{size}", str(len(file_bytes)))

    log_step("Router",     "Database",
             "Datei auf Disk speichern",
             "Bytes werden in uploads/<timestamp>_dateiname geschrieben. filepath-Spalte wird befüllt.")

    # Save to disk
    safe_filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path     = UPLOAD_DIR / safe_filename
    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    # Text extraction
    content_text = None
    suffix       = Path(file.filename).suffix.lower()
    if suffix == ".txt":
        content_text = file_bytes.decode("utf-8", errors="ignore").strip() or None
    elif suffix == ".pdf":
        try:
            import io
            from pypdf import PdfReader
            reader       = PdfReader(io.BytesIO(file_bytes))
            content_text = "\n".join(p.extract_text() or "" for p in reader.pages).strip() or None
        except Exception:
            content_text = None

    extracted = f"{len(content_text)} Zeichen extrahiert." if content_text else "Kein Text (gescanntes PDF oder unbekanntes Format)."
    log_step("Router",     "AIService",
             "Text-Extraktion (RAG Vorbereitung)",
             f"pypdf liest alle Seiten der '{suffix}'-Datei. {extracted} "
             "content-Spalte speichert den Rohtext für die RAG-Pipeline.")

    # Save to DB
    new_doc = Document(
        title=title, filepath=str(file_path),
        content=content_text, category=category, uploaded_by=uploaded_by
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    log_step("AIService",  "PostgreSQL",
             "Dokument in DB persistiert",
             f"models.py legt neuen Eintrag in documents-Tabelle an. "
             f"id={new_doc.id}, category='{category}', content={'gesetzt' if content_text else 'NULL'}.")
    log_step("PostgreSQL", "Schema",
             "Response-Validierung",
             "SQLAlchemy-Objekt → Pydantic DocumentResponse. "
             "content-Feld wird absichtlich weggelassen (zu groß für Listen-Responses).")
    log_step("Schema",     "User",
             "201 Created → Swagger + Simulator",
             f"Admin sieht 201 Created in Swagger. "
             f"Simulator empfängt automatisch alle {len(get_trace())} Schritte via WebSocket.")

    # ── Broadcast trace to all connected simulators ───────────────────
    # This runs async – simulators animate immediately, no button needed
    await manager.broadcast_trace(
        trace    = get_trace(),
        endpoint = f"POST /api/documents/upload ({title})"
    )

    # Also attach to header as fallback (for non-WebSocket clients)
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