"""Tool log service."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tool_log import ToolLog


class ToolLogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_recent(self, limit: int = 50, offset: int = 0) -> list[ToolLog]:
        result = await self.db.execute(
            select(ToolLog)
            .order_by(ToolLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
