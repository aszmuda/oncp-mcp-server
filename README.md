## Application Resolution MCP Server

This project hosts an MCP-compatible SSE server that lets LLM clients trigger and monitor automated resolution jobs via a downstream FastAPI service.

### Prerequisites
1. Copy the env template and update the downstream URL:
   ```bash
   cp .env.example .env
   ```
2. Ensure the target FastAPI service is reachable from this host.

### Run the SSE server
```bash
uv run python main.py
```
- The server binds to `http://localhost:${MCP_SSE_PORT:-8000}/sse` (messages flow via `/messages/`).
- Logs report when the transport starts and when shutdown completes.

### Client connection examples
- **MCP CLI**: `npx @modelcontextprotocol/cli connect http://localhost:8000 --transport sse`
- **Raw SSE testing**: `curl -N http://localhost:8000/sse`

Once connected, call the tools exposed by the server:
1. `start_resolution` – launch a job and receive a `job_id`.
2. `check_resolution_status` – poll the current status (QUEUED/RUNNING/COMPLETED/FAILED).
3. `get_resolution_reasoning` – read the agent’s Markdown reasoning for that job.

Use `Ctrl+C` to stop the server gracefully; shutdown hooks ensure HTTP clients are torn down cleanly.

### Testing & Verification

1. **Unit tests** (httpx client mocking):
   ```bash
   uv run pytest
   ```
2. **Integration smoke test** (spins up a mock downstream API, the MCP SSE server, and an SSE client):
   ```bash
   uv run python scripts/smoke_test.py
   ```
   Expected output:
   - Mock service and SSE server startup messages
   - Tool responses printed inline (job ID, status, reasoning snippet)
   - `Smoke test succeeded ✅` on completion

For manual verification, you can also connect using the MCP CLI command above; a successful run will stream SSE events and return tool results identical to the smoke test.
