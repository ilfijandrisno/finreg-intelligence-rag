"""FastAPI application entrypoint, lifespan, middleware assembly, and router registration."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from finreg import __version__
from finreg.api.middleware import (
    RequestTracingMiddleware,
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from finreg.api.routers.health import router as health_router
from finreg.api.routers.rag import router as rag_router
from finreg.api.routers.retrieval import router as retrieval_router
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
    description="Production REST API for Grounded Indonesian Financial Regulations",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 1. Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Add Request Tracing Middleware (X-Request-ID propagation)
app.add_middleware(RequestTracingMiddleware)

# 3. Register Custom Exception Handlers
app.add_exception_handler(RequestValidationError, cast(Any, validation_exception_handler))
app.add_exception_handler(HTTPException, cast(Any, http_exception_handler))
app.add_exception_handler(Exception, global_exception_handler)

# 4. Register API Routers
app.include_router(health_router)
app.include_router(rag_router)
app.include_router(retrieval_router)
