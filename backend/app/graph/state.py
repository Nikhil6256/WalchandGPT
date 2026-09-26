"""
LangGraph Agent State definition.
Strongly-typed state object passed between all graph nodes.
"""
import operator
from typing import Annotated, Any, Optional
from typing_extensions import TypedDict


class Citation(TypedDict):
    document_id: str
    document_title: str
    chunk_content: str
    page_number: Optional[int]
    similarity_score: float
    department: Optional[str]


class AgentState(TypedDict):
    """
    Immutable-style state threaded through every LangGraph node.
    Nodes return partial dicts; LangGraph merges them.
    """
    # Identity
    user_id: str
    conversation_id: str

    # The current user question
    query: str

    # Classified intent (set by classify_query node)
    intent: str

    # Conversation memory passed to LLM (trimmed to token budget)
    chat_history: list[dict[str, str]]

    # RAG
    retrieved_documents: Annotated[list[dict[str, Any]], operator.add]
    context_quality: str  # "sufficient" | "partial" | "insufficient"
    reformulated_query: Optional[str]

    # Tool results from MCP server
    tool_results: Annotated[list[dict[str, Any]], operator.add]

    # Final answer and citations
    answer: str
    citations: list[Citation]

    # Confidence: high | medium | low
    confidence: str

    # Streaming status events (shown to user as agent progress)
    status_events: Annotated[list[str], operator.add]

    # Observability
    retrieval_latency_ms: Optional[float]
    llm_latency_ms: Optional[float]
    total_latency_ms: Optional[float]
    llm_tokens_used: Optional[int]

    # Error tracking
    error: Optional[str]
    retry_count: int
