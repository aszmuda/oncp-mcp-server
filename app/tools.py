"""MCP tool registrations for the Application Resolution server."""

import logging
from dataclasses import dataclass
from typing import Annotated, Awaitable, Callable

from fastmcp import Context, FastMCP
from pydantic import Field

from app.client import ResolutionApiClient, ResolutionApiError

logger = logging.getLogger(__name__)


@dataclass
class ResolutionToolDependencies:
    """Runtime dependencies required by the MCP tools."""

    resolution_client: ResolutionApiClient | None = None

    def attach_client(self, client: ResolutionApiClient) -> None:
        self.resolution_client = client

    def detach_client(self) -> None:
        self.resolution_client = None

    def require_client(self) -> ResolutionApiClient:
        if self.resolution_client is None:
            raise RuntimeError("Resolution API client is not initialized.")
        return self.resolution_client


def register_resolution_tools(
    mcp: FastMCP,
    dependencies: ResolutionToolDependencies,
) -> None:
    """Register MCP tools that proxy to the downstream Resolution API."""

    def _validate_non_empty(value: str, field_name: str) -> str:
        if not value or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string.")
        return value.strip()

    def _log_tool_event(tool_name: str, event: str, **fields: object) -> None:
        logger.info(
            "resolution_tool_event",
            extra={"tool": tool_name, "event": event, **fields},
        )

    async def _with_error_handling(
        tool_name: str,
        action: Callable[[], Awaitable[dict[str, str]]],
    ) -> dict[str, str]:
        try:
            return await action()
        except ResolutionApiError as exc:
            logger.warning("%s failed due to API error", tool_name, exc_info=True)
            _log_tool_event(tool_name, "api_error", error=str(exc))
            return {"error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            logger.exception("%s failed unexpectedly", tool_name)
            _log_tool_event(tool_name, "unexpected_error", error=str(exc))
            return {"error": f"Unexpected error: {exc}"}

    @mcp.tool(
        name="start_resolution",
        description="Trigger an asynchronous analysis/resolution job for a service issue.",
    )
    async def start_resolution(
        hostname: Annotated[str, Field(description="Hostname or identifier of the affected system.")],
        error_code: Annotated[str, Field(description="Error code or shorthand identifier for the issue.")],
        issue_description: Annotated[str, Field(description="Detailed description of the observed issue.")],
        ctx: Context,
    ) -> dict[str, str]:
        """Launch a downstream resolution job and return its job ID."""

        hostname_value = _validate_non_empty(hostname, "hostname")
        error_code_value = _validate_non_empty(error_code, "error_code")
        issue_description_value = _validate_non_empty(issue_description, "issue_description")

        client = dependencies.require_client()

        async def _call() -> dict[str, str]:
            response = await client.launch_resolution(
                hostname=hostname_value,
                error_code=error_code_value,
                issue_description=issue_description_value,
            )
            job_id = response.get("job_id", "")
            if not job_id:
                raise ResolutionApiError("Resolution API response did not include a job_id.")

            result = {
                "job_id": job_id,
                "status": response.get("status", "UNKNOWN"),
                "message": "Resolution job queued successfully.",
            }
            await ctx.info(f"Resolution job {job_id} queued.")
            _log_tool_event(
                "start_resolution",
                "success",
                job_id=job_id,
                status=result["status"],
            )
            return result

        return await _with_error_handling("start_resolution", _call)

    @mcp.tool(
        name="check_resolution_status",
        description="Check the latest status for a previously launched resolution job.",
    )
    async def check_resolution_status(
        job_id: Annotated[str, Field(description="Job identifier returned by start_resolution.")],
    ) -> dict[str, str]:
        """Return the current lifecycle state for the requested job."""

        job_id_value = _validate_non_empty(job_id, "job_id")
        client = dependencies.require_client()

        async def _call() -> dict[str, str]:
            response = await client.get_job_status(job_id_value)
            status = response.get("status", "UNKNOWN")
            result = {
                "job_id": response.get("job_id", job_id_value),
                "status": status,
            }
            _log_tool_event(
                "check_resolution_status",
                "success",
                job_id=result["job_id"],
                status=status,
            )
            return result

        return await _with_error_handling("check_resolution_status", _call)

    @mcp.tool(
        name="get_resolution_reasoning",
        description="Retrieve the agent's detailed reasoning and remediation steps for a job.",
    )
    async def get_resolution_reasoning(
        job_id: Annotated[str, Field(description="Job identifier returned by start_resolution.")],
    ) -> dict[str, str]:
        """Return diagnostic/analysis text captured by the downstream agent."""

        job_id_value = _validate_non_empty(job_id, "job_id")
        client = dependencies.require_client()

        async def _call() -> dict[str, str]:
            response = await client.get_job_analysis(job_id_value)
            thoughts = response.get("thoughts", "")
            if not thoughts:
                thoughts = "No analysis was provided for this job."
            result = {
                "job_id": response.get("job_id", job_id_value),
                "thoughts": thoughts,
            }
            _log_tool_event(
                "get_resolution_reasoning",
                "success",
                job_id=result["job_id"],
                has_thoughts=bool(thoughts.strip()),
            )
            return result

        return await _with_error_handling("get_resolution_reasoning", _call)

    logger.info("Resolution MCP tools registered.")

