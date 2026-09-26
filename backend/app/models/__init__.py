"""
Models package — import Base and all ORM models so Alembic can discover them.
"""
from app.db.base import Base  # noqa: F401

# Import all models to register them with Base.metadata
from app.models.user import User  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.document import Document, DocumentChunk  # noqa: F401
from app.models.feedback import Feedback  # noqa: F401
from app.models.tool_log import ToolLog  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401

__all__ = [
    "Base",
    "User",
    "Conversation",
    "Message",
    "Document",
    "DocumentChunk",
    "Feedback",
    "ToolLog",
    "AuditLog",
]
