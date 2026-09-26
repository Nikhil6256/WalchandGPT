"""
MCP Client — wraps HTTP calls to the MCP server.
The LangGraph agent uses this to invoke college-specific tools.
Falls back gracefully when the MCP server is unavailable.
"""
from typing import Any, Optional

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)

# Maximum time to wait for an MCP tool response
MCP_TIMEOUT = 30.0


class MCPClient:
    """
    Async HTTP client for the WalchandGPT MCP server.
    Implements circuit-breaker-style fallback: returns empty result
    on connection failure rather than crashing the agent.
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._available: bool = False

    async def connect(self) -> None:
        """Initialize the HTTP client and check MCP server health."""
        self._client = httpx.AsyncClient(
            base_url=settings.MCP_SERVER_URL,
            timeout=MCP_TIMEOUT,
        )
        try:
            resp = await self._client.get("/health")
            self._available = resp.status_code == 200
            log.info("MCP server connected", available=self._available, url=settings.MCP_SERVER_URL)
        except Exception as e:
            log.warning("MCP server unavailable at startup", error=str(e))
            self._available = False

    async def disconnect(self) -> None:
        """Close the HTTP client on shutdown."""
        if self._client:
            await self._client.aclose()

    async def call_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
    ) -> Any:
        """
        Call a named tool on the MCP server.
        Returns the tool's result or raises MCPToolError on failure.
        """
        if not self._available or not self._client:
            raise MCPUnavailableError("MCP server is not available")

        try:
            resp = await self._client.post(
                f"/tools/{tool_name}",
                json=parameters,
            )
            resp.raise_for_status()
            return resp.json().get("result", {})
        except httpx.HTTPStatusError as e:
            log.error("MCP tool error", tool=tool_name, status=e.response.status_code)
            raise MCPToolError(f"Tool {tool_name} returned {e.response.status_code}") from e
        except httpx.RequestError as e:
            log.error("MCP request failed", tool=tool_name, error=str(e))
            self._available = False  # Mark as unavailable for circuit-breaker
            raise MCPUnavailableError(f"MCP server unreachable: {e}") from e

    async def list_tools(self) -> list[dict]:
        """Return all available MCP tools from the server."""
        if not self._available or not self._client:
            return []
        try:
            resp = await self._client.get("/tools")
            resp.raise_for_status()
            return resp.json().get("tools", [])
        except Exception:
            return []

    @property
    def is_available(self) -> bool:
        return self._available


class MCPToolError(Exception):
    """Raised when an MCP tool returns an error response."""


class MCPUnavailableError(Exception):
    """Raised when the MCP server cannot be reached."""


# Singleton client instance
mcp_client = MCPClient()
