"""ToolLog model — records every MCP/agent tool invocation."""
import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ToolStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"


class ToolLog(Base):
    __tablename__ = "tool_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    input_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    execution_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[ToolStatus] = mapped_column(
        Enum(ToolStatus), default=ToolStatus.SUCCESS, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<ToolLog {self.tool_name} {self.status.value}>"
