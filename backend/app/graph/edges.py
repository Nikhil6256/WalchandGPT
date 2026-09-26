"""
LangGraph conditional edge routing functions.
Each function inspects AgentState and returns the name of the next node.
"""
from app.graph.state import AgentState

# Intents that benefit from MCP tool calls
TOOL_INTENTS = {"timetable_query", "notice_query", "faculty_query",
                "exam_query", "event_query", "placement_query"}

# Intents that need RAG retrieval
RAG_INTENTS = {"knowledge_base_question"} | TOOL_INTENTS


def route_after_classify(state: AgentState) -> str:
    """After classification, decide whether to retrieve, use a tool, or answer directly."""
    intent = state.get("intent", "general_question")

    if intent == "general_question":
        return "generate_direct_answer"
    elif intent in TOOL_INTENTS:
        return "call_mcp_tool"
    else:
        # knowledge_base_question and fallback
        return "retrieve_context"


def route_after_tool(state: AgentState) -> str:
    """After MCP tool call, decide whether to also run RAG retrieval."""
    # If tool returned results, skip retrieval to save latency
    if state.get("tool_results"):
        return "generate_answer"
    # Tool failed — fall back to RAG
    return "retrieve_context"


def route_after_grade(state: AgentState) -> str:
    """After grading context quality, decide whether to generate or reformulate."""
    quality = state.get("context_quality", "insufficient")
    retry_count = state.get("retry_count", 0)

    if quality == "sufficient":
        return "generate_answer"
    elif quality == "partial":
        # Partial context is still usable — generate with a caveat
        return "generate_answer"
    elif retry_count >= 1:
        # Already reformulated once — generate with what we have
        return "generate_answer"
    else:
        # First time insufficient — try reformulating and re-retrieving
        return "reformulate_query"
