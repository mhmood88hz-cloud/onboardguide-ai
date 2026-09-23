import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import User, Document, DocumentImage
from app.schemas import DocumentResponse
from app.security import require_verwaltung, get_current_user, load_current_user
from app.services.trace import start_trace, log_step, get_trace
from app.services.ws_manager import manager
from app.services.chunking_service import embed_document

router    = APIRouter(prefix="/api/documents", tags=["Documents"])
UPLOAD_DIR  = Path("uploads")
IMAGES_DIR  = UPLOAD_DIR / "images"
UPLOAD_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

# Bilder kleiner als das (Breite*Höhe) sind Bullet-Icons/Deko aus dem PDF-Layout,
# keine echten Screenshots – die wollen wir nicht im Chat anzeigen.
MIN_IMAGE_PIXELS = 100 * 100


def _extract_pdf(file_bytes: bytes) -> tuple[str | None, list[tuple[int, bytes, str]]]:
    """
    Extrahiert Text (mit "<<<PAGE:n>>>"-Markern für die seitenbewusste RAG-
    Chunking-Pipeline) sowie eingebettete Screenshots/Bilder je Seite.
    Gibt (content_text, [(page_number, image_bytes, extension), ...]) zurück.
    """
    import io
    from pypdf import PdfReader

    reader        = PdfReader(io.BytesIO(file_bytes))
    text_parts    = []
    images_found  = []

    for page_index, page in enumerate(reader.pages):
        page_number = page_index + 1
        page_text   = page.extract_text() or ""
        text_parts.append(f"<<<PAGE:{page_number}>>>\n{page_text}")

        try:
            for img in page.images:
                try:
                    width, height = img.image.size
                except Exception:
                    continue
                if width * height < MIN_IMAGE_PIXELS:
                    continue
                ext = Path(img.name).suffix.lstrip(".") or "png"
                images_found.append((page_number, img.data, ext))
        except Exception:
            pass

    content_text = "\n".join(text_parts).strip() or None
    return content_text, images_found


@router.get("/{document_id}/images/{image_id}")
def get_document_image(
    document_id: int,
    image_id:    int,
    db:          Session = Depends(get_db),
    user_id:     int     = Depends(get_current_user)
):
    """Liefert ein aus einer PDF extrahiertes Bild aus – nur wenn der User
    laut Rolle/Kategorie Zugriff auf das zugehörige Dokument hat."""
    current_user = load_current_user(user_id, db)
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.organization_id == current_user.organization_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden!")

    if current_user.user_role != "Verwaltung":
        allowed = {"Allgemein"}
        if current_user.user_role == "Leader":
            for m in db.query(User).filter(User.reports_to == current_user.id).all():
                if m.department:       allowed.add(m.department)
                if m.assigned_project: allowed.add(m.assigned_project)
        else:
            if current_user.department:       allowed.add(current_user.department)
            if current_user.assigned_project: allowed.add(current_user.assigned_project)
        if doc.category not in allowed:
            raise HTTPException(status_code=403, detail="Kein Zugriff auf dieses Dokument!")

    image = db.query(DocumentImage).filter(
        DocumentImage.id == image_id,
        DocumentImage.document_id == document_id
    ).first()
    if not image or not Path(image.filepath).exists():
        raise HTTPException(status_code=404, detail="Bild nicht gefunden!")

    return FileResponse(image.filepath)


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    response:     Response,
    title:        str        = Form(...),
    category:     str        = Form(...),
    uploaded_by:  int        = Form(...),
    file:         UploadFile = File(...),
    db:           Session    = Depends(get_db),
    current_user: User       = Depends(require_verwaltung)
):
    if not db.query(User).filter(
        User.id == uploaded_by,
        User.organization_id == current_user.organization_id
    ).first():
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

    content_text  = None
    pdf_images    = []
    suffix        = Path(file.filename).suffix.lower()
    if suffix == ".txt":
        content_text = file_bytes.decode("utf-8", errors="ignore").strip() or None
    elif suffix == ".pdf":
        try:
            content_text, pdf_images = _extract_pdf(file_bytes)
        except Exception:
            content_text, pdf_images = None, []

    extracted = f"{len(content_text)} Zeichen extrahiert." if content_text else "Kein Text extrahiert."
    log_step("Router", "AIService",
             "Text-Extraktion (RAG Vorbereitung)",
             f"pypdf verarbeitet '{suffix}'-Datei. {extracted} "
             f"{len(pdf_images)} Bild(er) gefunden. "
             "content-Spalte speichert den Rohtext für die RAG-Pipeline.")

    new_doc = Document(
        organization_id=current_user.organization_id,
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

    saved_images = 0
    for page_number, image_bytes, ext in pdf_images:
        image_filename = f"doc{new_doc.id}_p{page_number}_{saved_images}.{ext}"
        image_path      = IMAGES_DIR / image_filename
        try:
            with open(image_path, "wb") as buffer:
                buffer.write(image_bytes)
        except Exception:
            continue
        db.add(DocumentImage(
            document_id=new_doc.id, page_number=page_number,
            sequence=saved_images, filepath=str(image_path)
        ))
        saved_images += 1
    if saved_images:
        db.commit()
        log_step("PostgreSQL", "PostgreSQL",
                 "Bilder gespeichert",
                 f"{saved_images} Screenshot(s) aus der PDF in document_images gespeichert.")

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
    query = db.query(Document).options(joinedload(Document.chunks)).filter(
        Document.organization_id == current_user.organization_id
    )
    if current_user.user_role == "Verwaltung":
        return query.all()
    allowed = {"Allgemein"}
    if current_user.user_role == "Leader":
        for m in db.query(User).filter(User.reports_to == current_user.id).all():
            if m.department:       allowed.add(m.department)
            if m.assigned_project: allowed.add(m.assigned_project)
    else:
        if current_user.department:       allowed.add(current_user.department)
        if current_user.assigned_project: allowed.add(current_user.assigned_project)
    return query.filter(Document.category.in_(allowed)).all()
