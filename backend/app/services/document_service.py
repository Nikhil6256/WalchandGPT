"""Document service: CRUD for documents."""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentType, IndexingStatus


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        title: str,
        file_path: str,
        file_name: str,
        document_type: DocumentType,
        description: Optional[str] = None,
        file_size: Optional[int] = None,
        department: Optional[str] = None,
        document_category: Optional[str] = None,
        uploaded_by: Optional[uuid.UUID] = None,
    ) -> Document:
        doc = Document(
            title=title,
            description=description,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            document_type=document_type,
            department=department,
            document_category=document_category,
            uploaded_by=uploaded_by,
            indexing_status=IndexingStatus.PENDING,
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def get_by_id(self, document_id: uuid.UUID) -> Optional[Document]:
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Document]:
        result = await self.db.execute(
            select(Document).order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, document_id: uuid.UUID) -> bool:
        doc = await self.get_by_id(document_id)
        if not doc:
            return False
        await self.db.delete(doc)
        await self.db.commit()
        return True

    async def update_status(
        self, document_id: uuid.UUID, status: IndexingStatus
    ) -> None:
        doc = await self.get_by_id(document_id)
        if doc:
            doc.indexing_status = status
            await self.db.commit()
