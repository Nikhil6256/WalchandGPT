"""
WalchandGPT MCP Server
======================
Exposes college-specific tools as HTTP endpoints.
The LangGraph agent calls these tools through the MCPClient.

Tools are logically separated from the main FastAPI app so they can be
deployed independently and scaled separately.
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from tools.college_tools import router as tools_router

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("MCP Server starting")
    yield
    log.info("MCP Server shutting down")


app = FastAPI(
    title="WalchandGPT MCP Server",
    description="Model Context Protocol server for college-specific tools",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(tools_router, prefix="/tools")


@app.get("/health")
async def health():
    return {"status": "ok", "server": "walchandgpt-mcp"}


@app.get("/tools")
async def list_tools():
    """Return metadata about all available tools (for tool discovery)."""
    return {
        "tools": [
            {
                "name": "get_timetable",
                "description": "Get class timetable by department, semester, division, and day",
                "parameters": ["department", "semester", "division", "day"],
            },
            {
                "name": "get_notices",
                "description": "Get recent college notices and announcements",
                "parameters": ["category", "limit"],
            },
            {
                "name": "get_faculty",
                "description": "Get faculty information by department or subject",
                "parameters": ["department", "subject", "query"],
            },
            {
                "name": "get_exam_schedule",
                "description": "Get examination schedule by department and semester",
                "parameters": ["department", "semester"],
            },
            {
                "name": "get_events",
                "description": "Get upcoming college events and activities",
                "parameters": ["category", "limit"],
            },
            {
                "name": "get_placement_statistics",
                "description": "Get placement statistics and company visit information",
                "parameters": ["year", "department"],
            },
            {
                "name": "get_department_info",
                "description": "Get information about a specific department",
                "parameters": ["department"],
            },
            {
                "name": "search_college_database",
                "description": "Search structured college data",
                "parameters": ["query", "category"],
            },
        ]
    }
