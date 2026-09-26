"""
Document management routes.
Admin: upload, delete, re-index. All: list documents.
Document indexing runs in the background (FastAPI BackgroundTasks).
"""
import uuid
from pathlib import Path
from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status

from app.core.config import settings
from app.core.deps import AdminUser, CurrentUser, DBDep
from app.models.audit_log import AuditLog
from app.models.document import Document, DocumentType, IndexingStatus
from app.rag.pipeline import run_ingestion_pipeline
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.services.document_service import DocumentService
from app.services.storage_service import StorageService

log = structlog.get_logger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".pptx", ".xlsx"}
MAX_FILE_SIZE_MB = 50


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    db: DBDep,
    admin: AdminUser,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    document_category: Optional[str] = Form(None),
):
    """
    Upload a document to the knowledge base.
    File processing (chunking, embedding) runs asynchronously.
    """
    # Validate file extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {suffix!r} not allowed. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # Validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_FILE_SIZE_MB}MB limit",
        )

    # Store the file
    storage = StorageService()
    file_path = await storage.save(content, file.filename or "upload", subdirectory="documents")

    doc_type = DocumentType(suffix.lstrip(".")) if suffix.lstrip(".") in [t.value for t in DocumentType] else DocumentType.OTHER

    # Create database record
    doc_service = DocumentService(db)
    document = await doc_service.create(
        title=title,
        description=description,
        file_path=file_path,
        file_name=file.filename or "upload",
        file_size=len(content),
        document_type=doc_type,
        department=department,
        document_category=document_category,
        uploaded_by=admin.id,
    )

    # Audit
    db.add(AuditLog(
        user_id=admin.id,
        action="document_upload",
        resource_type="document",
        resource_id=str(document.id),
        details={"title": title, "filename": file.filename},
    ))
    await db.commit()

    # Trigger background ingestion (non-blocking)
    background_tasks.add_task(
        run_ingestion_pipeline,
        document_id=document.id,
        file_path=file_path,
        db=db,
    )

    log.info("Document uploaded", document_id=str(document.id), title=title)
    return DocumentResponse.model_validate(document)


@router.get("", response_model=DocumentListResponse)
async def list_documents(current_user: CurrentUser, db: DBDep):
    """List all indexed documents."""
    doc_service = DocumentService(db)
    docs = await doc_service.list_all()
    return DocumentListResponse(documents=docs)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    admin: AdminUser,
    db: DBDep,
):
    """Delete a document and all its chunks from the knowledge base."""
    doc_service = DocumentService(db)
    doc = await doc_service.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Delete from storage
    storage = StorageService()
    await storage.delete(doc.file_path)

    await doc_service.delete(document_id)

    db.add(AuditLog(
        user_id=admin.id,
        action="document_delete",
        resource_type="document",
        resource_id=str(document_id),
        details={"title": doc.title},
    ))
    await db.commit()


@router.post("/{document_id}/reindex", response_model=DocumentResponse)
async def reindex_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    admin: AdminUser,
    db: DBDep,
):
    """Re-run the ingestion pipeline for an existing document."""
    doc_service = DocumentService(db)
    doc = await doc_service.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Reset status
    await doc_service.update_status(document_id, IndexingStatus.PENDING)

    background_tasks.add_task(
        run_ingestion_pipeline,
        document_id=doc.id,
        file_path=doc.file_path,
        db=db,
    )

    return DocumentResponse.model_validate(doc)
