"""Health check endpoints."""

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Returns service health status",
)
async def health_check() -> HealthResponse:
    """Check if the service is healthy.

    Returns:
        Health status response
    """
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Returns service readiness status for k8s probes",
)
async def readiness_check() -> HealthResponse:
    """Check if the service is ready to accept requests.

    This endpoint can be extended to check database connectivity,
    cache availability, etc.

    Returns:
        Readiness status response
    """
    # TODO: Add database connectivity check
    return HealthResponse(status="ok")
