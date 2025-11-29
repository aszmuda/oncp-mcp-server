"""Entry point for the Application Resolution MCP server."""

import logging
import os

from app.server import build_server
from app.settings import Settings


def _configure_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main() -> None:
    """Bootstrap and run the SSE server."""
    _configure_logging()
    logger = logging.getLogger("oncp-mcp-server")
    settings = Settings.load()
    server = build_server(settings)

    try:
        server.startup()
        logger.info(
            "MCP SSE server ready at http://localhost:%s/sse",
            settings.mcp_sse_port,
        )
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutdown requested (Ctrl+C).")
    except Exception:
        logger.exception("Server stopped due to an unexpected error.")
        raise
    finally:
        server.shutdown()
        logger.info("Server shutdown complete.")


if __name__ == "__main__":
    main()
