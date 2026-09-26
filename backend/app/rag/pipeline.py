"""
Document ingestion pipeline: load → clean → chunk → embed → store.
Each step is separated for testability and observability.
"""
import asyncio
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import structlog
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.llm.provider import get_embeddings
from app.models.document import Document as DocumentModel, DocumentChunk, IndexingStatus
from app.rag.loaders import load_document

log = structlog.get_logger(__name__)

# Token-aware splitter (RecursiveCharacterTextSplitter handles most formats well)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP,
    length_function=len,
    separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
)


async def run_ingestion_pipeline(
    document_id: uuid.UUID,
    file_path: str,
    db: AsyncSession,
    extra_metadata: Optional[dict[str, Any]] = None,
) -> None:
    """
    Full ingestion pipeline for a single document.
    Runs in background (called by FastAPI BackgroundTasks).

    Steps:
      1. Update status → PROCESSING
      2. Load and extract text
      3. Clean and chunk text
      4. Generate embeddings
      5. Store chunks in PostgreSQL with pgvector embeddings
      6. Update status → COMPLETED / FAILED
    """
    t0 = time.perf_counter()
    log.info("Ingestion started", document_id=str(document_id), path=file_path)

    # Fetch document record
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == document_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        log.error("Document not found", document_id=str(document_id))
        return

    try:
        # Step 1: Mark as processing
        document.indexing_status = IndexingStatus.PROCESSING
        await db.commit()

        # Step 2: Load and extract text
        raw_documents = await asyncio.to_thread(load_document, file_path)
        if not raw_documents:
            raise ValueError(f"No content extracted from {file_path}")

        log.info("Document loaded", pages=len(raw_documents))

        # Step 3: Add document-level metadata to each page
        base_metadata = {
            "document_id": str(document_id),
            "title": document.title,
            "department": document.department,
            "document_type": document.document_type.value,
            **(extra_metadata or {}),
            **(document.doc_metadata or {}),
        }
        for doc in raw_documents:
            doc.metadata.update(base_metadata)

        # Step 4: Chunk text
        chunks = text_splitter.split_documents(raw_documents)
        log.info("Text chunked", chunk_count=len(chunks))

        if not chunks:
            raise ValueError("Chunking produced no output")

        # Step 5: Generate embeddings in batches (avoid rate limits)
        embeddings_model = get_embeddings()
        chunk_texts = [c.page_content for c in chunks]
        embeddings = await embeddings_model.aembed_documents(chunk_texts)

        log.info("Embeddings generated", count=len(embeddings))

        # Step 6: Delete existing chunks (for re-indexing)
        from sqlalchemy import delete
        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )

        # Step 7: Bulk insert chunks
        chunk_records = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_records.append(
                DocumentChunk(
                    document_id=document_id,
                    content=chunk.page_content,
                    embedding=embedding,
                    chunk_index=idx,
                    page_number=chunk.metadata.get("page"),
                    chunk_metadata={
                        k: v for k, v in chunk.metadata.items()
                        if k not in ("document_id", "title")
                    },
                )
            )

        db.add_all(chunk_records)

        # Step 8: Update document status
        document.indexing_status = IndexingStatus.COMPLETED
        document.chunk_count = len(chunk_records)
        document.error_message = None
        await db.commit()

        elapsed = (time.perf_counter() - t0) * 1000
        log.info(
            "Ingestion complete",
            document_id=str(document_id),
            chunks=len(chunk_records),
            latency_ms=elapsed,
        )

    except Exception as e:
        log.error("Ingestion failed", document_id=str(document_id), error=str(e))
        document.indexing_status = IndexingStatus.FAILED
        document.error_message = str(e)[:2000]
        await db.commit()
