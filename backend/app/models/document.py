"""Document and DocumentChunk models for the RAG knowledge base."""
import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base


class DocumentType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"
    PPTX = "pptx"
    XLSX = "xlsx"
    OTHER = "other"


class IndexingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)  # storage reference
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), nullable=False)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    indexing_status: Mapped[IndexingStatus] = mapped_column(
        Enum(IndexingStatus), default=IndexingStatus.PENDING, nullable=False
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Rich metadata: semester, academic_year, source, etc.
    doc_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    uploaded_by_user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="documents"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document {self.title} ({self.indexing_status.value})>"


class DocumentChunk(Base):
    """
    A single text chunk from a document, with its vector embedding.
    Uses pgvector for efficient ANN search.
    """
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Vector stored in pgvector column; dimension matches embedding model
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSION), nullable=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # chunk-level metadata: section, heading, department, etc.
    chunk_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk {self.id} doc={self.document_id} idx={self.chunk_index}>"
