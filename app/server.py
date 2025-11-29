"""
Core server bootstrap for the Application Resolution MCP server.

Phase 4 wires up the fastmcp instance and registers the required MCP tools.
"""

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP  # type: ignore[import-not-found]

from app.client import ResolutionApiClient
from app.settings import Settings
from app.tools import ResolutionToolDependencies, register_resolution_tools


class ServerApp:
    """Placeholder server container for future dependency injection."""

    def __init__(self, settings: Settings) -> None:
        self._logger = logging.getLogger(__name__)
        self._settings = settings
        self._state: dict[str, Any] = {"settings": settings}
        self._resolution_client: ResolutionApiClient | None = None
        self._tool_dependencies = ResolutionToolDependencies()
        self._mcp_app = FastMCP(
            name="Application Resolution MCP Server",
            instructions=(
                "Trigger, monitor, and inspect automated resolution jobs for application issues."
            ),
            port=settings.mcp_sse_port,
        )
        register_resolution_tools(self._mcp_app, self._tool_dependencies)
        self._state["mcp_app"] = self._mcp_app

    def startup(self) -> None:
        """Prepare resources required to launch the SSE server."""
        self._logger.info("Starting server bootstrap")
        self._resolution_client = ResolutionApiClient.from_settings(self._settings)
        self._tool_dependencies.attach_client(self._resolution_client)
        self._state["initialized"] = True

    def shutdown(self) -> None:
        """Release acquired resources."""
        self._logger.info("Shutting down server bootstrap")
        if self._resolution_client is not None:
            asyncio.run(self._resolution_client.aclose())
            self._resolution_client = None
        self._tool_dependencies.detach_client()
        self._state.clear()

    def serve_forever(self) -> None:
        """Run the FastMCP SSE server until interrupted."""
        host = "0.0.0.0"
        port = self._settings.mcp_sse_port
        self._logger.info("Starting SSE transport", extra={"host": host, "port": port})
        self._mcp_app.run(transport="sse", host=host, port=port)

    async def serve_sse_async(self, host: str = "0.0.0.0") -> None:
        """Async helper for running the SSE transport (used by smoke tests)."""
        await self._mcp_app.run_http_async(
            transport="sse",
            host=host,
            port=self._settings.mcp_sse_port,
        )

    @property
    def mcp(self) -> FastMCP:
        """Expose the configured FastMCP instance."""
        return self._mcp_app


def build_server(settings: Settings) -> ServerApp:
    """Factory used by main.py to create the configured server instance."""
    return ServerApp(settings)

