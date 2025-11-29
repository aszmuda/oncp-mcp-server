## Development Plan: Application Resolution MCP Server

### Goal Overview
Build a Python 3.12+ MCP server (via fastmcp) that lets an LLM launch asynchronous resolution jobs against an external FastAPI service, monitor their progress, and fetch reasoning logs via an SSE-accessible transport. The server should rely on uv for dependency management, expose three MCP tools, and be configurable via environment variables.

### Phases & Key Steps
1. **Project scaffolding & tooling**
   - Initialize the uv-managed project (`pyproject.toml`, `uv.lock`) targeting Python 3.12+.
   - Add core dependencies: `fastmcp`, `httpx`, `python-dotenv`, and any quality-of-life tools (logging, typing stubs).
   - Define `main.py` entry point structure and prepare package layout (e.g., `app/` or similar).

2. **Configuration management**
   - Define `.env.example` covering `RESOLUTION_SERVICE_URL`, optional `API_TIMEOUT`, `MCP_SSE_PORT`.
   - Implement a small config loader (e.g., `settings.py`) that reads env vars via `python-dotenv`, applies defaults, and validates required values.
   - Ensure configuration is injected into both the HTTP client and SSE server bootstrap.

3. **External FastAPI client (`client.py`)**
   - Build an async `httpx.AsyncClient` wrapper with base URL, timeout, and retry/backoff strategy if desired.
   - Implement helper methods: `launch_resolution(payload)`, `get_job_status(job_id)`, `get_agent_analysis(job_id)`.
   - Centralize response parsing, error normalization, and logging so MCP tools can stay lean.

4. **MCP tool implementations (`main.py`)**
   - Initialize fastmcp server instance, register tools with `@mcp.tool`.
   - Tool behaviors:
     - `start_resolution`: validate strings, format payload, call client, return `job_id`.
     - `check_resolution_status`: accept `job_id`, call status endpoint, map API status to friendly output.
     - `get_resolution_reasoning`: fetch analysis text, return Markdown/plaintext as-is.
   - Keep tool bodies async, handle exceptions (network issues, HTTP errors) with user-friendly messages.

5. **SSE transport configuration**
   - Use fastmcp’s SSE support (or compatible middleware) to expose an HTTP endpoint listening on configurable `MCP_SSE_PORT`.
   - Document how clients connect (curl example, fastmcp CLI command, etc.).
   - Ensure graceful shutdown and health logging.

6. **Error handling, validation, and observability**
   - Enforce non-empty string parameters before making HTTP calls.
   - Wrap httpx errors, timeout issues, and non-2xx responses with informative messages including response body when possible.
   - Add structured logging (tool name, job_id, status) to aid debugging.

7. **Testing & verification**
   - Write unit tests or lightweight async tests for `client.py` using httpx mock utilities.
   - Optionally provide integration smoke script to hit a mocked FastAPI service.
   - Verify SSE endpoint manually (e.g., with curl) and confirm MCP tools behave end-to-end.

### Dependencies, Risks, and Considerations
- **External API availability:** Development/testing requires either the real FastAPI service or a mock; clarify contract early to avoid blockers.
- **SSE requirement:** fastmcp SSE transport must be supported by deployment target; confirm hosting environment and firewall rules.
- **Env configuration:** Missing or misconfigured `RESOLUTION_SERVICE_URL` or ports will break connectivity; add startup validation.
- **Timeouts/retries:** Long-running resolution jobs may need generous HTTP timeouts; document expectations and consider exponential backoff.
- **Version alignment:** Track fastmcp and httpx versions for compatibility with Python 3.12 and uv; pin in `pyproject.toml`.
- **Security/compliance:** If the FastAPI service requires auth (future requirement), design client to plug in headers/tokens without rework.

