"""Conversation service: CRUD + message history retrieval."""
import uuid
from typing import Optional

import structlog
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole

log = structlog.get_logger(__name__)


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: uuid.UUID, title: str = "New Conversation") -> Conversation:
        conv = Conversation(user_id=user_id, title=title[:512])
        self.db.add(conv)
        await self.db.commit()
        await self.db.refresh(conv)
        return conv

    async def get_by_id(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            return False
        await self.db.delete(conv)
        await self.db.commit()
        return True

    async def get_recent_messages(
        self, conversation_id: uuid.UUID, limit: int = 10
    ) -> list[dict[str, str]]:
        """
        Return the last N user+assistant messages as a list of dicts
        suitable for passing to the LLM as chat history.
        """
        result = await self.db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.role.in_([MessageRole.USER, MessageRole.ASSISTANT]),
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = list(reversed(result.scalars().all()))
        return [{"role": msg.role.value, "content": msg.content} for msg in messages]
