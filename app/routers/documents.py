import shutil

from datetime import datetime, timezone
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Document
from app.schemas import DocumentResponse
from app.security import verify_admin_token, get_current_user, load_current_user

router = APIRouter(prefix="/api/documents", tags=["Documents"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload", response_model=DocumentResponse, status_code=201,
             dependencies=[Depends(verify_admin_token)])
async def upload_document(
    title:       str        = Form(...),
    category:    str        = Form(...),
    uploaded_by: int        = Form(...),
    file:        UploadFile = File(...),
    db:          Session    = Depends(get_db)
):
    """
    Uploads a document, saves it locally, and extracts text for RAG.
    Reads all bytes first to avoid stream-exhaustion when passing to pypdf.
    """
    # Read entire file into memory first
    file_bytes = await file.read()

    # Save to disk
    safe_filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path     = UPLOAD_DIR / safe_filename
    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    # Extract text content
    content_text = None
    suffix       = Path(file.filename).suffix.lower()

    if suffix == ".txt":
        content_text = file_bytes.decode("utf-8", errors="ignore").strip() or None

    elif suffix == ".pdf":
        try:
            import io
            from pypdf import PdfReader
            reader       = PdfReader(io.BytesIO(file_bytes))
            pages        = [page.extract_text() or "" for page in reader.pages]
            content_text = "\n".join(pages).strip() or None
        except ImportError:
            content_text = None
        except Exception:
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


@router.get("", response_model=List[DocumentResponse])
def get_documents(
    db:      Session = Depends(get_db),
    user_id: int     = Depends(get_current_user)
):
    """
    Returns documents the requesting user is allowed to see.

    Access logic:
    - Verwaltung → all documents
    - Leader     → Allgemein + departments/projects of their team members
    - Mitarbeiter→ Allgemein + own department + own project
    """
    current_user = load_current_user(user_id, db)

    if current_user.user_role == "Verwaltung":
        return db.query(Document).all()

    allowed_categories = {"Allgemein"}

    if current_user.user_role == "Leader":
        team = db.query(User).filter(User.reports_to == current_user.id).all()
        for member in team:
            if member.department:
                allowed_categories.add(member.department)
            if member.assigned_project:
                allowed_categories.add(member.assigned_project)
    else:
        if current_user.department:
            allowed_categories.add(current_user.department)
        if current_user.assigned_project:
            allowed_categories.add(current_user.assigned_project)

    return db.query(Document).filter(Document.category.in_(allowed_categories)).all()