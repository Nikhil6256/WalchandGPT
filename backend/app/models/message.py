"""Message model — individual turns in a conversation."""
import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageType(str, enum.Enum):
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    SYSTEM_EVENT = "system_event"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType), default=MessageType.TEXT, nullable=False
    )
    # Stores citations, tool calls, confidence scores, latency, etc.
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(  # noqa: F821
        "Conversation", back_populates="messages"
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(  # noqa: F821
        "Feedback", back_populates="message"
    )

    def __repr__(self) -> str:
        return f"<Message {self.id} role={self.role.value}>"
