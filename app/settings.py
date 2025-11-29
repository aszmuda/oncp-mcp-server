"""Environment-driven configuration utilities for the MCP server."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    """Container for runtime configuration."""

    resolution_service_url: str
    api_timeout: float = 30.0
    mcp_sse_port: int = 8000

    @classmethod
    def load(cls) -> "Settings":
        """
        Load configuration from environment variables.

        Python-dotenv is used so developers can rely on a local .env file without
        exporting variables globally.
        """
        load_dotenv()

        resolution_service_url = os.getenv("RESOLUTION_SERVICE_URL", "").strip()
        if not resolution_service_url:
            raise ValueError("RESOLUTION_SERVICE_URL is required but was not provided.")

        api_timeout_raw = os.getenv("API_TIMEOUT", "").strip() or "30"
        try:
            api_timeout = float(api_timeout_raw)
        except ValueError as exc:
            raise ValueError("API_TIMEOUT must be a numeric value.") from exc
        if api_timeout <= 0:
            raise ValueError("API_TIMEOUT must be greater than zero.")

        mcp_sse_port_raw = os.getenv("MCP_SSE_PORT", "").strip() or "8000"
        try:
            mcp_sse_port = int(mcp_sse_port_raw)
        except ValueError as exc:
            raise ValueError("MCP_SSE_PORT must be an integer.") from exc
        if mcp_sse_port <= 0:
            raise ValueError("MCP_SSE_PORT must be greater than zero.")

        return cls(
            resolution_service_url=resolution_service_url,
            api_timeout=api_timeout,
            mcp_sse_port=mcp_sse_port,
        )

