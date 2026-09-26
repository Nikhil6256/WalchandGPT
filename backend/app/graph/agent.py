"""
WalchandGPT LangGraph agent graph construction.

Graph topology:
  START
    ↓
  classify_query
    ↓ (conditional)
  ┌─────────────────────────────────────────┐
  │ general_question → generate_direct_answer│
  │ tool_intent      → call_mcp_tool         │
  │ rag_intent       → retrieve_context      │
  └─────────────────────────────────────────┘
                           ↓ (after tool)
              [grade_context or generate_answer]
                           ↓ (conditional)
              [generate_answer or reformulate_query]
                           ↓ (after reformulate → retrieve again)
                     generate_answer
                           ↓
                          END
"""
import functools
from typing import AsyncIterator, Any

import structlog
from langgraph.graph import StateGraph, START, END

from app.graph.edges import (
    route_after_classify,
    route_after_grade,
    route_after_tool,
)
from app.graph.nodes import (
    call_mcp_tool,
    classify_query,
    generate_answer,
    generate_direct_answer,
    grade_context,
    reformulate_query,
    retrieve_context,
)
from app.graph.state import AgentState

log = structlog.get_logger(__name__)


def build_agent_graph(retriever, mcp_client) -> StateGraph:
    """
    Construct and compile the WalchandGPT LangGraph workflow.

    Dependencies (retriever and mcp_client) are injected via functools.partial
    so nodes remain pure, testable functions that only accept AgentState.
    """
    graph = StateGraph(AgentState)

    # ── Register nodes with injected dependencies ─────────────────────────
    graph.add_node("classify_query", classify_query)
    graph.add_node(
        "retrieve_context",
        functools.partial(retrieve_context, retriever=retriever),
    )
    graph.add_node("grade_context", grade_context)
    graph.add_node("reformulate_query", reformulate_query)
    graph.add_node(
        "call_mcp_tool",
        functools.partial(call_mcp_tool, mcp_client=mcp_client),
    )
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("generate_direct_answer", generate_direct_answer)

    # ── Edges ─────────────────────────────────────────────────────────────
    graph.add_edge(START, "classify_query")

    graph.add_conditional_edges(
        "classify_query",
        route_after_classify,
        {
            "generate_direct_answer": "generate_direct_answer",
            "call_mcp_tool": "call_mcp_tool",
            "retrieve_context": "retrieve_context",
        },
    )

    graph.add_conditional_edges(
        "call_mcp_tool",
        route_after_tool,
        {
            "generate_answer": "generate_answer",
            "retrieve_context": "retrieve_context",
        },
    )

    graph.add_edge("retrieve_context", "grade_context")

    graph.add_conditional_edges(
        "grade_context",
        route_after_grade,
        {
            "generate_answer": "generate_answer",
            "reformulate_query": "reformulate_query",
        },
    )

    # After reformulation, retrieve again (second attempt)
    graph.add_edge("reformulate_query", "retrieve_context")

    graph.add_edge("generate_answer", END)
    graph.add_edge("generate_direct_answer", END)

    return graph.compile()


async def stream_agent_response(
    graph,
    initial_state: AgentState,
) -> AsyncIterator[dict[str, Any]]:
    """
    Stream LangGraph graph events as they occur.
    Yields dicts with 'type' and 'data' fields suitable for SSE.
    """
    async for event in graph.astream_events(initial_state, version="v2"):
        event_name = event.get("name", "")
        event_kind = event.get("event", "")

        # Status events from nodes
        if event_kind == "on_chain_end" and "status_events" in event.get("data", {}).get("output", {}):
            events = event["data"]["output"].get("status_events", [])
            for status in events:
                yield {"type": "status", "data": status}

        # LLM token streaming
        elif event_kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield {"type": "token", "data": chunk.content}

        # Graph completion
        elif event_kind == "on_chain_end" and event_name == "LangGraph":
            output = event.get("data", {}).get("output", {})
            yield {
                "type": "done",
                "data": {
                    "answer": output.get("answer", ""),
                    "citations": output.get("citations", []),
                    "confidence": output.get("confidence", "medium"),
                    "intent": output.get("intent", ""),
                    "retrieval_latency_ms": output.get("retrieval_latency_ms"),
                    "llm_latency_ms": output.get("llm_latency_ms"),
                },
            }
