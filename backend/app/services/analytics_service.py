"""Analytics service for admin dashboard."""
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.document import Document, IndexingStatus
from app.models.feedback import Feedback
from app.models.message import Message, MessageRole
from app.models.tool_log import ToolLog
from app.schemas.admin import AnalyticsResponse


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_analytics(self) -> AnalyticsResponse:
        # Total conversations
        total_convs = (await self.db.execute(
            select(func.count(Conversation.id))
        )).scalar_one()

        # Total messages
        total_msgs = (await self.db.execute(
            select(func.count(Message.id))
        )).scalar_one()

        # Total documents
        total_docs = (await self.db.execute(
            select(func.count(Document.id))
        )).scalar_one()

        # Feedback counts
        helpful = (await self.db.execute(
            select(func.count(Feedback.id)).where(Feedback.rating == 1)
        )).scalar_one()

        not_helpful = (await self.db.execute(
            select(func.count(Feedback.id)).where(Feedback.rating == -1)
        )).scalar_one()

        total_feedback = helpful + not_helpful
        helpful_pct = (helpful / total_feedback * 100) if total_feedback > 0 else 0.0

        # Documents by status
        docs_by_status = {}
        for status in IndexingStatus:
            count = (await self.db.execute(
                select(func.count(Document.id)).where(Document.indexing_status == status)
            )).scalar_one()
            docs_by_status[status.value] = count

        # Tool usage (top tools by name)
        tool_rows = (await self.db.execute(
            select(ToolLog.tool_name, func.count(ToolLog.id).label("cnt"))
            .group_by(ToolLog.tool_name)
            .order_by(func.count(ToolLog.id).desc())
            .limit(10)
        )).fetchall()
        tool_usage = {row.tool_name: row.cnt for row in tool_rows}

        return AnalyticsResponse(
            total_conversations=total_convs,
            total_messages=total_msgs,
            total_documents=total_docs,
            helpful_count=helpful,
            not_helpful_count=not_helpful,
            helpful_percentage=round(helpful_pct, 1),
            top_intents=[],  # TODO: extract from message metadata
            avg_retrieval_latency_ms=None,
            avg_llm_latency_ms=None,
            documents_by_status=docs_by_status,
            tool_usage_count=tool_usage,
        )
