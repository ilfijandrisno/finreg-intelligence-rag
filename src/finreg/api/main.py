"""FastAPI application entrypoint and foundation routers."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from finreg import __version__
from finreg.config.settings import get_settings
from finreg.observability.logging import setup_logging

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifespan context manager."""
    settings = get_settings()
    logger.info(
        "Starting %s v%s in %s environment",
        settings.app_name,
        __version__,
        settings.environment,
    )
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title="FinReg Intelligence API",
    description="Grounding API for Indonesian Financial Regulations (BI & OJK)",
    version=__version__,
    lifespan=lifespan,
)


class HealthResponse(BaseModel):
    """Schema for lightweight health check response."""

    status: str
    service: str
    version: str


@app.get("/health", response_model=HealthResponse, tags=["System"])
def get_health() -> dict[str, str]:
    """Lightweight application health status check endpoint."""
    return {
        "status": "ok",
        "service": "finreg-intelligence",
        "version": __version__,
    }
