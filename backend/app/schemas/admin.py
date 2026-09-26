"""Admin analytics Pydantic schemas."""
from typing import Optional
from pydantic import BaseModel


class AnalyticsResponse(BaseModel):
    total_conversations: int
    total_messages: int
    total_documents: int
    helpful_count: int
    not_helpful_count: int
    helpful_percentage: float
    top_intents: list[dict]
    avg_retrieval_latency_ms: Optional[float]
    avg_llm_latency_ms: Optional[float]
    documents_by_status: dict[str, int]
    tool_usage_count: dict[str, int]


class ToolLogResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    tool_name: str
    status: str
    execution_time_ms: Optional[float]
    created_at: str


class ToolLogListResponse(BaseModel):
    logs: list[ToolLogResponse]
    total: int
