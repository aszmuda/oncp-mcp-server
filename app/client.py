"""
Resolution API client wrapper for interacting with the FastAPI service.

Phase 3 introduces typed helper methods that encapsulate request/response
handling, including consistent error reporting and logging.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.http_client import create_resolution_client
from app.settings import Settings

logger = logging.getLogger(__name__)


class ResolutionApiError(RuntimeError):
    """Represents failures when communicating with the downstream service."""


def _require_non_empty(value: str, field_name: str) -> str:
    """Normalize and validate non-empty request arguments."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return cleaned


@dataclass(slots=True)
class ResolutionApiClient:
    """Typed wrapper around the shared AsyncClient."""

    _client: httpx.AsyncClient

    @classmethod
    def from_settings(cls, settings: Settings) -> "ResolutionApiClient":
        """Factory that builds the client from Settings."""
        return cls(create_resolution_client(settings))

    async def aclose(self) -> None:
        """Close the underlying HTTP resources."""
        await self._client.aclose()

    async def launch_resolution(
        self,
        *,
        hostname: str,
        error_code: str,
        issue_description: str,
    ) -> dict[str, Any]:
        """Trigger a new resolution job and return the job payload."""
        hostname_clean = _require_non_empty(hostname, "hostname")
        error_code_clean = _require_non_empty(error_code, "error_code")
        issue_description_clean = _require_non_empty(issue_description, "issue_description")

        payload = {
            "error": error_code_clean,
            "hostname": hostname_clean,
            "message": issue_description_clean,
        }
        logger.debug(
            "Launching resolution job",
            extra={"hostname": hostname_clean, "error_code": error_code_clean},
        )
        return await self._request("POST", "/resolve", json=payload)

    async def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Retrieve the status for a given job."""
        job_id_clean = _require_non_empty(job_id, "job_id")
        logger.debug("Fetching job status", extra={"job_id": job_id_clean})
        return await self._request("GET", f"/jobs/{job_id_clean}/status")

    async def get_job_analysis(self, job_id: str) -> dict[str, Any]:
        """Retrieve the agent reasoning/analysis for a given job."""
        job_id_clean = _require_non_empty(job_id, "job_id")
        logger.debug("Fetching job analysis", extra={"job_id": job_id_clean})
        return await self._request("GET", f"/jobs/{job_id_clean}/analysis")

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Normalized request handler for all outgoing API calls."""

        def _transport_error(message: str, *, exc: Exception | None = None) -> ResolutionApiError:
            logger.error(
                message,
                extra={"method": method, "path": path},
                exc_info=exc,
            )
            return ResolutionApiError(message)

        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise _transport_error(
                f"Resolution API request timed out ({method} {path}).",
                exc=exc,
            ) from exc
        except httpx.RequestError as exc:
            raise _transport_error(
                f"Resolution API request failed ({method} {path}): {exc!s}",
                exc=exc,
            ) from exc

        if response.is_error:
            snippet = response.text.strip()
            if len(snippet) > 512:
                snippet = f"{snippet[:512]}..."
            logger.warning(
                "Resolution API responded with error",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "content": snippet,
                },
            )
            raise ResolutionApiError(
                f"Resolution API error ({response.status_code}) during {method} {path}: {snippet or 'no body provided.'}"
            )

        try:
            data: dict[str, Any] = response.json()
        except json.JSONDecodeError as exc:
            logger.error(
                "Resolution API returned invalid JSON",
                extra={"method": method, "path": path},
            )
            raise ResolutionApiError(
                f"Resolution API returned invalid JSON during {method} {path}."
            ) from exc

        return data

