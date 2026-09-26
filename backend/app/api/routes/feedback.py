"""Feedback routes: submit thumbs up/down ratings on assistant messages."""
import uuid

import structlog
from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DBDep
from app.models.feedback import Feedback
from app.models.message import Message
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.feedback_service import FeedbackService

log = structlog.get_logger(__name__)
router = APIRouter()


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackRequest,
    current_user: CurrentUser,
    db: DBDep,
):
    """Submit rating feedback on an assistant message."""
    if payload.rating not in (1, -1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be 1 (helpful) or -1 (not helpful)",
        )

    service = FeedbackService(db)
    feedback = await service.create(
        message_id=payload.message_id,
        user_id=current_user.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    return FeedbackResponse.model_validate(feedback)
