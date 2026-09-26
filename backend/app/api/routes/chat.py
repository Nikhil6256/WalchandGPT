"""
Chat streaming endpoint.
Uses Server-Sent Events (SSE) to stream LangGraph agent events to the frontend.
"""
import json
import time
import uuid
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.agents.mcp_client import mcp_client
from app.core.deps import CurrentUser, DBDep
from app.graph.agent import build_agent_graph, stream_agent_response
from app.graph.state import AgentState
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole, MessageType
from app.rag.retriever import HybridRetriever
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.conversation_service import ConversationService

log = structlog.get_logger(__name__)
router = APIRouter()

MAX_HISTORY_MESSAGES = 10  # Limit context window to last N messages


@router.post("/chat/stream")
async def stream_chat(
    payload: ChatRequest,
    request: Request,
    current_user: CurrentUser,
    db: DBDep,
):
    """
    Main streaming chat endpoint.
    Accepts a user message, runs the LangGraph agent, and streams back:
      - status events (e.g. "Searching knowledge base...")
      - LLM tokens as they arrive
      - final metadata (citations, confidence, latency)
    """
    t_start = time.perf_counter()
    conversation_service = ConversationService(db)

    # Resolve or create conversation
    if payload.conversation_id:
        conversation = await conversation_service.get_by_id(
            payload.conversation_id, current_user.id
        )
        if not conversation:
            conversation = await conversation_service.create(
                user_id=current_user.id, title=payload.message[:60]
            )
    else:
        conversation = await conversation_service.create(
            user_id=current_user.id, title=payload.message[:60]
        )

    # Load recent conversation history (bounded to MAX_HISTORY_MESSAGES)
    history = await conversation_service.get_recent_messages(
        conversation.id, limit=MAX_HISTORY_MESSAGES
    )

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=payload.message,
        message_type=MessageType.TEXT,
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    # Build retriever and agent graph (per-request, uses request-scoped DB session)
    retriever = HybridRetriever(db)
    graph = build_agent_graph(retriever=retriever, mcp_client=mcp_client)

    initial_state: AgentState = {
        "user_id": str(current_user.id),
        "conversation_id": str(conversation.id),
        "query": payload.message,
        "intent": "",
        "chat_history": history,
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

    async def event_generator() -> AsyncGenerator[str, None]:
        """SSE generator that yields formatted event strings."""
        final_state = {}
        accumulated_answer = []

        try:
            # Send conversation ID immediately so frontend can track
            yield _sse_event("metadata", {
                "conversation_id": str(conversation.id),
                "message_id": str(user_msg.id),
            })

            async for event in stream_agent_response(graph, initial_state):
                if event["type"] == "status":
                    yield _sse_event("status", {"message": event["data"]})

                elif event["type"] == "token":
                    accumulated_answer.append(event["data"])
                    yield _sse_event("token", {"content": event["data"]})

                elif event["type"] == "done":
                    final_state = event["data"]
                    total_latency = (time.perf_counter() - t_start) * 1000

                    # Persist assistant message
                    answer = final_state.get("answer", "".join(accumulated_answer))
                    assistant_msg = Message(
                        conversation_id=conversation.id,
                        role=MessageRole.ASSISTANT,
                        content=answer,
                        message_type=MessageType.TEXT,
                        metadata_={
                            "citations": final_state.get("citations", []),
                            "confidence": final_state.get("confidence", "medium"),
                            "intent": final_state.get("intent", ""),
                            "retrieval_latency_ms": final_state.get("retrieval_latency_ms"),
                            "llm_latency_ms": final_state.get("llm_latency_ms"),
                            "total_latency_ms": total_latency,
                        },
                    )
                    db.add(assistant_msg)
                    await db.commit()
                    await db.refresh(assistant_msg)

                    yield _sse_event("done", {
                        "message_id": str(assistant_msg.id),
                        "citations": final_state.get("citations", []),
                        "confidence": final_state.get("confidence", "medium"),
                        "total_latency_ms": total_latency,
                    })

        except Exception as e:
            log.error("Streaming error", error=str(e))
            yield _sse_event("error", {"message": "An error occurred. Please try again."})

        finally:
            yield _sse_event("end", {})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(event_type: str, data: dict) -> str:
    """Format data as a Server-Sent Event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
