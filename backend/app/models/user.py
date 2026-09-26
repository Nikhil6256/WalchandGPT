"""User model with RBAC roles."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    STUDENT = "student"
    FACULTY = "faculty"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.STUDENT, nullable=False
    )
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year: Mapped[int | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(  # noqa: F821
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        "Document", back_populates="uploaded_by_user"
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(  # noqa: F821
        "Feedback", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"
