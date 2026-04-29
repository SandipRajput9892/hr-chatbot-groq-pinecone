import os
from datetime import datetime
from typing import List

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import get_current_admin, get_current_employee
from app.database import get_db
from app.models.db_models import Document, Employee
from app.models.request import ChatRequest
from app.models.response import ChatResponse, DocumentResponse, MessageResponse
from app.services.chat_service import chat_with_hr
from app.services.ingest_service import ingest_pdf
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _sync_upload_dir(db: Session, fallback_uploader_id) -> None:
    """Register AND index any PDFs in uploads/ not yet tracked or with chunks=0."""
    if not os.path.isdir(settings.UPLOAD_DIR):
        return
    changed = False
    for fname in os.listdir(settings.UPLOAD_DIR):
        if not fname.lower().endswith(".pdf"):
            continue
        original = fname.split("_", 1)[1] if "_" in fname else fname
        existing = db.query(Document).filter(Document.filename == original).first()
        if existing and existing.chunks > 0:
            continue  # already indexed — skip
        file_path = os.path.join(settings.UPLOAD_DIR, fname)
        result = ingest_pdf(file_path, source_name=original)
        chunks = result.get("chunks", 0) if result.get("status") == "success" else 0
        if existing:
            existing.chunks = chunks
            existing.file_path = file_path
        else:
            db.add(Document(
                filename=original,
                file_path=file_path,
                chunks=chunks,
                uploaded_by=fallback_uploader_id,
            ))
        changed = True
    if changed:
        try:
            db.commit()
        except Exception:
            db.rollback()


# ── Chat ──────────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    result = chat_with_hr(db, employee, request.message, source_filter=request.source)
    return ChatResponse(message=result["message"], sources=result["sources"])


# ── Documents ─────────────────────────────────────────────────────────────────

@router.get("/documents", response_model=List[DocumentResponse])
def list_documents(
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    _sync_upload_dir(db, employee.id)
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            chunks=d.chunks,
            uploaded_at=d.uploaded_at,
            uploader_name=d.uploader.name if d.uploader else None,
        )
        for d in docs
    ]


# ── PDF Upload ────────────────────────────────────────────────────────────────

@router.post("/upload-pdf", response_model=MessageResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    employee: Employee = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are accepted")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE // 1024 // 1024} MB",
        )

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = f"{employee.employee_id}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    logger.info(f"Employee {employee.employee_id} uploaded: {file.filename}")
    result = ingest_pdf(file_path, source_name=file.filename)

    if result["status"] == "error":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result["message"])

    # Upsert Document record so the file appears in the document list immediately
    existing = db.query(Document).filter(Document.filename == file.filename).first()
    if existing:
        existing.chunks = result["chunks"]
        existing.file_path = file_path
        existing.uploaded_by = employee.id
        existing.uploaded_at = datetime.utcnow()
    else:
        db.add(Document(
            filename=file.filename,
            file_path=file_path,
            chunks=result["chunks"],
            uploaded_by=employee.id,
        ))
    db.commit()

    return MessageResponse(message="PDF uploaded and ingested successfully", data=result)
