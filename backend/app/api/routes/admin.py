"""Admin-only routes: analytics, tool logs, user management."""
import structlog
from fastapi import APIRouter

from app.core.deps import AdminUser, DBDep
from app.schemas.admin import AnalyticsResponse, ToolLogListResponse
from app.services.analytics_service import AnalyticsService
from app.services.tool_log_service import ToolLogService

log = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(admin: AdminUser, db: DBDep):
    """
    Return aggregated analytics for the admin dashboard.
    Includes: total queries, helpful %, most common intents,
    RAG retrieval stats, tool usage.
    """
    service = AnalyticsService(db)
    return await service.get_analytics()


@router.get("/tool-logs", response_model=ToolLogListResponse)
async def get_tool_logs(admin: AdminUser, db: DBDep, limit: int = 50, offset: int = 0):
    """Return paginated tool execution logs."""
    service = ToolLogService(db)
    logs = await service.list_recent(limit=limit, offset=offset)
    return ToolLogListResponse(logs=logs, total=len(logs))
