"""
Integration smoke test for the Application Resolution MCP server.

This script spins up:
1. A mock Resolution FastAPI-compatible service (Starlette) that exposes the
   expected /resolve, /jobs/{id}/status, and /jobs/{id}/analysis endpoints.
2. The MCP SSE server (running in-process via FastMCP's HTTP transport).
3. A FastMCP client that connects over SSE, invokes the three tools, and prints
   the responses.

Usage:
    uv run python scripts/smoke_test.py

The script prints the tool outputs and exits with code 0 if the end-to-end flow
works. Use Ctrl+C to abort.
"""

import asyncio
import contextlib
import os
import uuid
from dataclasses import dataclass, field
from typing import Any

import uvicorn
from fastmcp.client import Client
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.server import build_server
from app.settings import Settings

MOCK_SERVICE_HOST = "127.0.0.1"
MOCK_SERVICE_PORT = 9070
SSE_HOST = "127.0.0.1"
SSE_PORT = 18080


@dataclass
class MockJobStore:
    """In-memory state store for the smoke test's pretend resolution jobs."""

    jobs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def create(self, hostname: str, error: str, message: str) -> dict[str, Any]:
        job_id = f"{uuid.uuid4()}"
        self.jobs[job_id] = {
            "status": "RUNNING",
            "thoughts": f"[{hostname}] {error} -> {message}",
        }
        return {"job_id": job_id, "status": "QUEUED"}

    def status(self, job_id: str) -> dict[str, Any]:
        job = self.jobs.get(job_id)
        if not job:
            return {"job_id": job_id, "status": "UNKNOWN"}
        # Promote job to COMPLETED after first status check.
        if job["status"] == "RUNNING":
            job["status"] = "COMPLETED"
        return {"job_id": job_id, "status": job["status"]}

    def analysis(self, job_id: str) -> dict[str, Any]:
        job = self.jobs.get(job_id)
        if not job:
            return {"job_id": job_id, "thoughts": "No analysis available."}
        return {"job_id": job_id, "thoughts": job["thoughts"]}


async def resolve_endpoint(request: Request) -> JSONResponse:
    payload = await request.json()
    result = request.app.state.jobs.create(
        hostname=payload["hostname"],
        error=payload["error"],
        message=payload["message"],
    )
    return JSONResponse(result)


async def job_status_endpoint(request: Request) -> JSONResponse:
    job_id = request.path_params["job_id"]
    return JSONResponse(request.app.state.jobs.status(job_id))


async def job_analysis_endpoint(request: Request) -> JSONResponse:
    job_id = request.path_params["job_id"]
    return JSONResponse(request.app.state.jobs.analysis(job_id))


def build_mock_service() -> Starlette:
    app = Starlette(
        routes=[
            Route("/resolve", resolve_endpoint, methods=["POST"]),
            Route("/jobs/{job_id:str}/status", job_status_endpoint, methods=["GET"]),
            Route("/jobs/{job_id:str}/analysis", job_analysis_endpoint, methods=["GET"]),
        ],
    )
    app.state.jobs = MockJobStore()
    return app


async def run_uvicorn_app(app: Starlette, host: str, port: int) -> uvicorn.Server:
    config = uvicorn.Config(app, host=host, port=port, log_level="error")
    server = uvicorn.Server(config)

    async def _serve() -> None:
        await server.serve()

    asyncio.create_task(_serve())
    # Give the server a moment to bind the port.
    await asyncio.sleep(0.3)
    return server


async def run_smoke_flow() -> None:
    print("Starting mock Resolution API service...")
    mock_server = await run_uvicorn_app(build_mock_service(), MOCK_SERVICE_HOST, MOCK_SERVICE_PORT)

    os.environ["RESOLUTION_SERVICE_URL"] = f"http://{MOCK_SERVICE_HOST}:{MOCK_SERVICE_PORT}"
    os.environ["MCP_SSE_PORT"] = str(SSE_PORT)
    settings = Settings.load()

    app_server = build_server(settings)
    app_server.startup()

    async def _run_sse() -> None:
        await app_server.serve_sse_async(host=SSE_HOST)

    print("Starting MCP SSE server...")
    sse_task = asyncio.create_task(_run_sse())
    await asyncio.sleep(0.5)

    client = Client(f"http://{SSE_HOST}:{SSE_PORT}", name="smoke-client")

    try:
        async with client:
            print("Calling start_resolution tool...")
            start_result = await client.call_tool(
                "start_resolution",
                {
                    "hostname": "smoke-host",
                    "error_code": "SMOKE-1",
                    "issue_description": "Demonstration failure",
                },
            )
            print("start_resolution result:", start_result)
            job_id = start_result["job_id"]

            status_result = await client.call_tool(
                "check_resolution_status",
                {"job_id": job_id},
            )
            print("check_resolution_status result:", status_result)

            reasoning_result = await client.call_tool(
                "get_resolution_reasoning",
                {"job_id": job_id},
            )
            print("get_resolution_reasoning result:", reasoning_result)

            print("Smoke test succeeded ✅")
    finally:
        print("Stopping MCP SSE server...")
        sse_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sse_task
        app_server.shutdown()

        print("Stopping mock Resolution API service...")
        mock_server.should_exit = True
        await asyncio.sleep(0.2)


if __name__ == "__main__":
    try:
        asyncio.run(run_smoke_flow())
    except KeyboardInterrupt:
        print("Smoke test interrupted.")

