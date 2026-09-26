"""Feedback Pydantic schemas."""
import uuid
from typing import Optional
from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    message_id: uuid.UUID
    rating: int  # 1 = helpful, -1 = not helpful
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    message_id: uuid.UUID
    rating: int
    comment: Optional[str]
