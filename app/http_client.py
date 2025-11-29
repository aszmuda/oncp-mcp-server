"""HTTP client factory for interacting with the FastAPI resolution service."""

import httpx

from app.settings import Settings


def create_resolution_client(settings: Settings) -> httpx.AsyncClient:
    """
    Build an AsyncClient configured for the downstream resolution service.

    Additional middleware (auth, retries, etc.) can be layered in future phases.
    """
    return httpx.AsyncClient(
        base_url=settings.resolution_service_url,
        timeout=settings.api_timeout,
    )

