"""Health and readiness probe router."""

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from finreg import __version__
from finreg.api.schemas import HealthResponse, ReadinessResponse
from finreg.database.connection import get_engine

logger = logging.getLogger("finreg.api.routers.health")

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse, summary="Application Liveness Probe")
def get_health() -> HealthResponse:
    """Check application process liveness.

    Always returns HTTP 200 OK if the FastAPI process is running.
    """
    return HealthResponse(
        status="ok",
        service="finreg-intelligence",
        version=__version__,
    )


@router.get(
    "/readiness",
    response_model=ReadinessResponse,
    summary="Database & Runtime Readiness Probe",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Database disconnected"}},
)
def get_readiness() -> ReadinessResponse:
    """Check application readiness including PostgreSQL database connectivity.

    Returns HTTP 200 OK if database is reachable, or HTTP 503 if disconnected.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return ReadinessResponse(status="ready", database="connected")
    except Exception as exc:
        logger.error("Readiness check failed: Database connection error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unreachable or disconnected",
        ) from exc
