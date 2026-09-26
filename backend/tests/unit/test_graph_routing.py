"""Unit tests for query classification and graph routing."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.graph.edges import route_after_classify, route_after_grade, route_after_tool
from app.graph.state import AgentState


def make_state(**kwargs) -> AgentState:
    """Helper to create a minimal valid AgentState for testing."""
    defaults: AgentState = {
        "user_id": "test-user",
        "conversation_id": "test-conv",
        "query": "test query",
        "intent": "general_question",
        "chat_history": [],
        "retrieved_documents": [],
        "context_quality": "",
        "reformulated_query": None,
        "tool_results": [],
        "answer": "",
        "citations": [],
        "confidence": "medium",
        "status_events": [],
        "retrieval_latency_ms": None,
        "llm_latency_ms": None,
        "total_latency_ms": None,
        "llm_tokens_used": None,
        "error": None,
        "retry_count": 0,
    }
    defaults.update(kwargs)
    return defaults


class TestRouteAfterClassify:
    def test_general_question_routes_to_direct_answer(self):
        state = make_state(intent="general_question")
        assert route_after_classify(state) == "generate_direct_answer"

    def test_knowledge_base_routes_to_retrieve(self):
        state = make_state(intent="knowledge_base_question")
        assert route_after_classify(state) == "retrieve_context"

    def test_timetable_routes_to_tool(self):
        state = make_state(intent="timetable_query")
        assert route_after_classify(state) == "call_mcp_tool"

    def test_faculty_routes_to_tool(self):
        state = make_state(intent="faculty_query")
        assert route_after_classify(state) == "call_mcp_tool"

    def test_exam_routes_to_tool(self):
        state = make_state(intent="exam_query")
        assert route_after_classify(state) == "call_mcp_tool"

    def test_notice_routes_to_tool(self):
        state = make_state(intent="notice_query")
        assert route_after_classify(state) == "call_mcp_tool"

    def test_unknown_intent_falls_back_to_retrieve(self):
        state = make_state(intent="unknown_intent_xyz")
        assert route_after_classify(state) == "retrieve_context"


class TestRouteAfterGrade:
    def test_sufficient_context_generates_answer(self):
        state = make_state(context_quality="sufficient", retry_count=0)
        assert route_after_grade(state) == "generate_answer"

    def test_partial_context_generates_answer(self):
        """Partial context is still usable — don't reformulate."""
        state = make_state(context_quality="partial", retry_count=0)
        assert route_after_grade(state) == "generate_answer"

    def test_insufficient_first_attempt_reformulates(self):
        state = make_state(context_quality="insufficient", retry_count=0)
        assert route_after_grade(state) == "reformulate_query"

    def test_insufficient_after_retry_generates(self):
        """After one reformulation, don't loop — generate with what we have."""
        state = make_state(context_quality="insufficient", retry_count=1)
        assert route_after_grade(state) == "generate_answer"


class TestRouteAfterTool:
    def test_tool_success_skips_retrieval(self):
        state = make_state(tool_results=[{"tool": "get_notices", "result": "..."}])
        assert route_after_tool(state) == "generate_answer"

    def test_tool_failure_falls_back_to_retrieval(self):
        state = make_state(tool_results=[])
        assert route_after_tool(state) == "retrieve_context"
