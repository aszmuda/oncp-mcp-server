import json
from typing import Any

import httpx
import pytest

from app.client import ResolutionApiClient, ResolutionApiError


def _build_client(handler: httpx.MockTransport) -> ResolutionApiClient:
    async_client = httpx.AsyncClient(transport=handler, base_url="http://mock.local")
    return ResolutionApiClient(async_client)


@pytest.mark.anyio
async def test_launch_resolution_success() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/resolve"
        payload = json.loads(request.content.decode())
        assert payload["hostname"] == "api-host"
        assert payload["error"] == "E123"
        assert payload["message"] == "Something broke"
        return httpx.Response(
            200,
            json={"job_id": "job-123", "status": "QUEUED"},
        )

    client = _build_client(httpx.MockTransport(handler))
    result = await client.launch_resolution(
        hostname="api-host",
        error_code="E123",
        issue_description="Something broke",
    )
    assert result["job_id"] == "job-123"
    assert result["status"] == "QUEUED"
    await client.aclose()


@pytest.mark.anyio
async def test_get_job_status_http_error_includes_details() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="Bad gateway from mock")

    client = _build_client(httpx.MockTransport(handler))
    with pytest.raises(ResolutionApiError) as exc:
        await client.get_job_status("job-123")
    assert "502" in str(exc.value)
    assert "Bad gateway from mock" in str(exc.value)
    await client.aclose()


@pytest.mark.anyio
async def test_timeout_surface_readable_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("mock timeout", request=request)

    client = _build_client(httpx.MockTransport(handler))
    with pytest.raises(ResolutionApiError) as exc:
        await client.get_job_analysis("job-123")
    assert "timed out" in str(exc.value)
    await client.aclose()


@pytest.mark.anyio
async def test_validation_rejects_empty_parameters() -> None:
    client = _build_client(httpx.MockTransport(lambda req: httpx.Response(200)))
    with pytest.raises(ValueError):
        await client.launch_resolution(hostname="  ", error_code="ERR", issue_description="desc")
    with pytest.raises(ValueError):
        await client.get_job_status("   ")
    await client.aclose()

