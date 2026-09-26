"""Conversation Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ConversationCreate(BaseModel):
    title: str = "New Conversation"


class MessageOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    metadata_: Optional[dict] = None


class ConversationResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []


class ConversationList(BaseModel):
    conversations: list[ConversationResponse]
