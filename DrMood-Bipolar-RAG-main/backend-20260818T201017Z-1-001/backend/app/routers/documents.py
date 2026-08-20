import io

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.services import vector_store

router = APIRouter(prefix="/api/documents", tags=["documents"])

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


@router.get("", response_model=list[schemas.DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return db.query(models.ClinicalDocument).order_by(models.ClinicalDocument.created_at.desc()).all()


@router.post("/upload", response_model=schemas.DocumentOut)
async def upload_document(
    title: str = Form(...),
    category: str = Form(""),
    page: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Ingest an approved clinical source (PDF or plain text) into the vector store
    so it becomes retrievable by /api/chat. This is meant to be an admin-only
    endpoint in production — add auth before exposing it publicly.
    """
    raw = await file.read()

    if file.filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(raw))
        text = "\n".join(page_obj.extract_text() or "" for page_obj in reader.pages)
    else:
        text = raw.decode("utf-8", errors="ignore")

    chunks = _chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="No extractable text found in the uploaded file")

    vector_store.add_chunks(chunks=chunks, title=title, category=category, page=page)

    doc = models.ClinicalDocument(title=title, category=category, page=page, chunk_count=len(chunks))
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.post("/text", response_model=schemas.DocumentOut)
def add_text_document(
    title: str = Form(...),
    category: str = Form(""),
    page: str = Form(""),
    text: str = Form(...),
    db: Session = Depends(get_db),
):
    """Ingest raw pasted text (e.g. a guideline excerpt) without a file upload."""
    chunks = _chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="Text is empty")

    vector_store.add_chunks(chunks=chunks, title=title, category=category, page=page)

    doc = models.ClinicalDocument(title=title, category=category, page=page, chunk_count=len(chunks))
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc
