"""Conversation service: CRUD + message history retrieval with resilient fallback."""
from datetime import datetime, timezone
import uuid
from typing import Optional

import structlog
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole

log = structlog.get_logger(__name__)

# In-memory storage when PostgreSQL is offline
FALLBACK_CONVERSATIONS: dict[uuid.UUID, Conversation] = {}
FALLBACK_MESSAGES: dict[uuid.UUID, list[Message]] = {}


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: uuid.UUID, title: str = "New Conversation") -> Conversation:
        conv = Conversation(
            id=uuid.uuid4(),
            user_id=user_id,
            title=title[:512],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        try:
            self.db.add(conv)
            await self.db.commit()
            await self.db.refresh(conv)
            return conv
        except Exception:
            pass

        FALLBACK_CONVERSATIONS[conv.id] = conv
        FALLBACK_MESSAGES[conv.id] = []
        return conv

    async def get_by_id(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Conversation]:
        try:
            result = await self.db.execute(
                select(Conversation)
                .options(selectinload(Conversation.messages))
                .where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
            conv = result.scalar_one_or_none()
            if conv:
                return conv
        except Exception:
            pass

        conv = FALLBACK_CONVERSATIONS.get(conversation_id)
        if conv and conv.user_id == user_id:
            return conv
        return None

    async def list_by_user(self, user_id: uuid.UUID) -> list[Conversation]:
        try:
            result = await self.db.execute(
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.updated_at.desc())
            )
            return list(result.scalars().all())
        except Exception:
            pass

        return [c for c in FALLBACK_CONVERSATIONS.values() if c.user_id == user_id]

    async def delete(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        try:
            result = await self.db.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
            conv = result.scalar_one_or_none()
            if conv:
                await self.db.delete(conv)
                await self.db.commit()
                return True
        except Exception:
            pass

        if conversation_id in FALLBACK_CONVERSATIONS:
            del FALLBACK_CONVERSATIONS[conversation_id]
            FALLBACK_MESSAGES.pop(conversation_id, None)
            return True
        return False

    async def get_recent_messages(
        self, conversation_id: uuid.UUID, limit: int = 10
    ) -> list[dict[str, str]]:
        """
        Return the last N user+assistant messages as a list of dicts
        suitable for passing to the LLM as chat history.
        """
        try:
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
        except Exception:
            pass

        msgs = FALLBACK_MESSAGES.get(conversation_id, [])
        filtered = [m for m in msgs if m.role in [MessageRole.USER, MessageRole.ASSISTANT]][-limit:]
        return [{"role": m.role.value, "content": m.content} for m in filtered]
