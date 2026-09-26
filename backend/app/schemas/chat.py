"""Chat Pydantic schemas."""
import uuid
from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[uuid.UUID] = None
    department_filter: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    citations: list[dict] = []
    confidence: str = "medium"
