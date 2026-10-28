"""
LangGraph node implementations.
Each node is a pure async function: AgentState -> partial AgentState dict.
Nodes do NOT import each other — they communicate only through state.
"""
import time
import re
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from app.graph.state import AgentState, Citation
from app.llm.prompts import (
    DIRECT_ANSWER_PROMPT,
    GRADER_PROMPT,
    RAG_PROMPT,
    REFORMULATE_PROMPT,
    TITLE_PROMPT,
)
from app.llm.provider import get_llm

log = structlog.get_logger(__name__)

# Intent categories that require MCP tool calls
TOOL_INTENTS = {"timetable_query", "notice_query", "faculty_query",
                "exam_query", "event_query", "placement_query"}

# Intent categories that require RAG retrieval
RAG_INTENTS = {"knowledge_base_question"} | TOOL_INTENTS


async def classify_query(state: AgentState) -> dict:
    """
    Node: Classify the user's intent to route the graph correctly.
    Uses a fast, cheap LLM call (low temperature for determinism).
    """
    q_lower = state["query"].lower().strip()
    # Fast heuristic routing to prevent multi-minute LLM reasoning delays on classification
    if re.match(r"^(hi|hello|hey|good morning|good evening|good afternoon)([!. ,]|$)", q_lower):
        intent = "general_question"
    elif any(k in q_lower for k in ["timetable", "schedule", "lecture", "period", "slot", "class time"]):
        intent = "timetable_query"
    elif any(k in q_lower for k in ["notice", "announcement", "circular", "notification", "cap round"]):
        intent = "notice_query"
    elif any(k in q_lower for k in ["faculty", "professor", "teacher", "hod", "dean", "director", "staff"]):
        intent = "faculty_query"
    elif any(k in q_lower for k in ["exam", "test", "midsem", "endsem", "semester exam"]):
        intent = "exam_query"
    elif any(k in q_lower for k in ["event", "fest", "hackathon", "workshop", "fdp", "vision"]):
        intent = "event_query"
    elif any(k in q_lower for k in ["placement", "package", "salary", "recruiter", "company", "ctc", "placed"]):
        intent = "placement_query"
    else:
        college_terms = (
            "walchand", "wce", "college", "campus", "admission", "department",
            "course", "academic", "hostel", "library", "scholarship", "syllabus",
            "eligibility", "fee", "fees", "student", "engineering", "attendance",
            "policy", "policies", "rule", "rules", "exam", "test", "midsem", "endsem",
            "cgpa", "sgpa", "atkt", "passing", "marks", "detention", "condonation",
            "timing", "timings", "office", "holiday", "vacation", "alumni", "founder"
        )
        intent = "knowledge_base_question" if any(term in q_lower for term in college_terms) else "general_question"

    return {
        "intent": intent,
        "status_events": [f"Classified as: {intent.replace('_', ' ')}"],
    }


async def retrieve_context(state: AgentState, retriever) -> dict:
    """
    Node: Perform hybrid retrieval (vector + keyword) from pgvector.
    The retriever is injected so this node stays testable.
    """
    log.info("retrieve_context", query=state.get("reformulated_query") or state["query"])
    t0 = time.perf_counter()

    query = state.get("reformulated_query") or state["query"]

    try:
        docs = await retriever.aretrieve(query, k=5)
        retrieved = [
            {
                "document_id": str(d.metadata.get("document_id", "")),
                "document_title": d.metadata.get("title", "Unknown"),
                "content": d.page_content,
                "page_number": d.metadata.get("page_number"),
                "similarity_score": d.metadata.get("score", 0.0),
                "department": d.metadata.get("department"),
            }
            for d in docs
        ]
    except Exception as e:
        log.error("retrieve_context failed", error=str(e))
        retrieved = []

    latency = (time.perf_counter() - t0) * 1000

    return {
        "retrieved_documents": retrieved,
        "context_quality": "partial" if retrieved else "insufficient",
        "retrieval_latency_ms": latency,
        "status_events": [f"Searched knowledge base ({len(retrieved)} chunks found)"],
    }


async def grade_context(state: AgentState) -> dict:
    """
    Node: Evaluate whether retrieved context is sufficient to answer the question.
    Returns: sufficient | partial | insufficient
    """
    log.info("grade_context", doc_count=len(state.get("retrieved_documents", [])))

    if not state.get("retrieved_documents"):
        return {"context_quality": "insufficient", "status_events": ["No relevant documents found"]}

    context = "\n\n".join(
        d["content"][:500] for d in state["retrieved_documents"][:3]
    )

    llm = get_llm(temperature=0.0)
    chain = GRADER_PROMPT | llm | StrOutputParser()

    try:
        quality = (await chain.ainvoke({
            "question": state["query"],
            "context": context,
        })).strip().lower()
        if quality not in ("sufficient", "partial", "insufficient"):
            quality = "partial"
    except Exception:
        quality = "partial"

    return {
        "context_quality": quality,
        "status_events": [f"Context quality: {quality}"],
    }


async def reformulate_query(state: AgentState) -> dict:
    """
    Node: Rewrite the question to improve retrieval on a second attempt.
    Only triggered when context_quality == insufficient.
    """
    log.info("reformulate_query")
    llm = get_llm(temperature=0.3)
    chain = REFORMULATE_PROMPT | llm | StrOutputParser()

    try:
        new_query = (await chain.ainvoke({"question": state["query"]})).strip()
    except Exception:
        new_query = state["query"]

    return {
        "reformulated_query": new_query,
        "retry_count": state.get("retry_count", 0) + 1,
        "status_events": ["Refining search query..."],
    }


async def call_mcp_tool(state: AgentState, mcp_client) -> dict:
    """
    Node: Call the appropriate MCP tool based on intent.
    The agent decides WHICH tool to call — not all intents trigger tools.
    """
    from app.agents.mcp_client import MCPClient
    intent = state["intent"]
    log.info("call_mcp_tool", intent=intent)

    tool_map = {
        "timetable_query": "get_timetable",
        "notice_query": "get_notices",
        "faculty_query": "get_faculty",
        "exam_query": "get_exam_schedule",
        "event_query": "get_events",
        "placement_query": "get_placement_statistics",
    }

    tool_name = tool_map.get(intent)
    if not tool_name:
        return {"tool_results": [], "status_events": []}

    try:
        result = await mcp_client.call_tool(
            tool_name=tool_name,
            parameters={"query": state["query"]},
        )
        return {
            "tool_results": [{"tool": tool_name, "result": result}],
            "status_events": [f"Queried college database via {tool_name}"],
        }
    except Exception as e:
        log.error("MCP tool call failed", tool=tool_name, error=str(e))
        return {
            "tool_results": [],
            "status_events": ["College database query failed — using knowledge base only"],
        }


async def generate_answer(state: AgentState) -> dict:
    """
    Node: Generate the final answer using retrieved context + tool results.
    Combines RAG context and MCP tool results into the LLM prompt.
    """
    log.info("generate_answer")
    t0 = time.perf_counter()

    for tool_result in state.get("tool_results", []):
        if tool_result.get("tool") != "get_notices":
            continue
        result = tool_result.get("result", {})
        notices = result.get("notices", []) if isinstance(result, dict) else []
        if notices:
            lines = ["Latest notices scraped from the official Walchand College website:"]
            for notice in notices:
                title = notice.get("title", "Official notice")
                date = notice.get("date")
                line = f"- **{title}**" + (f" ({date})" if date else "")
                if notice.get("link"):
                    line += f" - [Official notice]({notice['link']})"
                lines.append(line)
            return {
                "answer": "\n\n".join(lines),
                "citations": [],
                "confidence": "high",
                "llm_latency_ms": 0,
            }
        if isinstance(result, dict) and result.get("scraped") is False:
            return {
                "answer": result.get("note") or "No official notices could be retrieved right now.",
                "citations": [],
                "confidence": "low",
                "llm_latency_ms": 0,
            }

    # Build context from retrieved docs
    rag_context_parts = []
    for i, doc in enumerate(state.get("retrieved_documents", []), 1):
        title = doc.get("document_title", "Unknown")
        page = doc.get("page_number")
        page_str = f", Page {page}" if page else ""
        rag_context_parts.append(
            f"[{i}] Source: {title}{page_str}\n{doc['content']}"
        )

    # Append MCP tool results
    tool_parts = []
    for t in state.get("tool_results", []):
        tool_parts.append(f"[Tool: {t['tool']}]\n{t['result']}")

    context = "\n\n---\n\n".join(rag_context_parts + tool_parts)
    if not context:
        context = "No relevant context found in the knowledge base."

    # Build LangChain message history
    chat_history_msgs = []
    for msg in state.get("chat_history", []):
        if msg["role"] == "user":
            chat_history_msgs.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            chat_history_msgs.append(AIMessage(content=msg["content"]))

    llm = get_llm(streaming=True, temperature=0.1).bind(
        conversation_id=state["conversation_id"]
    )
    chain = RAG_PROMPT | llm | StrOutputParser()

    try:
        answer = await chain.ainvoke({
            "context": context,
            "chat_history": chat_history_msgs,
            "question": state["query"],
        })
    except Exception as e:
        log.error("generate_answer failed", error=str(e))
        answer = ("I'm sorry, I encountered an error generating a response. "
                  "Please try again.")
        return {"answer": answer, "citations": [], "confidence": "low", "error": str(e)}

    llm_latency = (time.perf_counter() - t0) * 1000

    # Build citations from retrieved documents
    citations: list[Citation] = [
        Citation(
            document_id=doc.get("document_id", ""),
            document_title=doc.get("document_title", "Unknown"),
            chunk_content=doc.get("content", "")[:500],
            page_number=doc.get("page_number"),
            similarity_score=doc.get("similarity_score", 0.0),
            department=doc.get("department"),
        )
        for doc in state.get("retrieved_documents", [])
        if doc.get("similarity_score", 0) > 0.3
    ]

    # Determine confidence based on context quality
    quality = state.get("context_quality", "partial")
    confidence = {"sufficient": "high", "partial": "medium", "insufficient": "low"}.get(
        quality, "medium"
    )

    return {
        "answer": answer,
        "citations": citations,
        "confidence": confidence,
        "llm_latency_ms": llm_latency,
        "status_events": ["Generating response..."],
    }


async def generate_direct_answer(state: AgentState) -> dict:
    """
    Node: Generate a response for general questions without RAG retrieval.
    """
    log.info("generate_direct_answer")
    t0 = time.perf_counter()

    if re.match(r"^(hi|hello|hey|good morning|good evening|good afternoon)([!. ,]|$)", state["query"].lower().strip()):
        return {
            "answer": "Hello! How can I help with Walchand College of Engineering?",
            "citations": [],
            "confidence": "high",
            "llm_latency_ms": 0,
        }

    chat_history_msgs = []
    for msg in state.get("chat_history", []):
        if msg["role"] == "user":
            chat_history_msgs.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            chat_history_msgs.append(AIMessage(content=msg["content"]))

    llm = get_llm(streaming=True, temperature=0.3).bind(
        conversation_id=state["conversation_id"]
    )
    chain = DIRECT_ANSWER_PROMPT | llm | StrOutputParser()

    try:
        answer = await chain.ainvoke({
            "chat_history": chat_history_msgs,
            "question": state["query"],
        })
    except Exception as e:
        log.error("generate_direct_answer failed", error=str(e))
        answer = "I'm sorry, I encountered an error. Please try again."

    llm_latency = (time.perf_counter() - t0) * 1000

    return {
        "answer": answer,
        "citations": [],
        "confidence": "high",
        "llm_latency_ms": llm_latency,
    }
