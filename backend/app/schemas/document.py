"""Document Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.document import DocumentType, IndexingStatus


class DocumentResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    title: str
    description: Optional[str]
    file_name: str
    document_type: DocumentType
    department: Optional[str]
    document_category: Optional[str]
    indexing_status: IndexingStatus
    chunk_count: int
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
