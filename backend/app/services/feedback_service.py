"""Feedback service."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.feedback import Feedback


class FeedbackService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        rating: int,
        comment: str | None = None,
    ) -> Feedback:
        feedback = Feedback(
            message_id=message_id,
            user_id=user_id,
            rating=rating,
            comment=comment,
        )
        self.db.add(feedback)
        await self.db.commit()
        await self.db.refresh(feedback)
        return feedback
