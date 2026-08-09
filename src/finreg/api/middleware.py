"""Middleware for request-ID tracing and strict exception information isolation."""

import logging
from uuid import uuid4

from fastapi import HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from finreg.api.schemas import ErrorResponse

logger = logging.getLogger("finreg.api.middleware")


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware propagating or generating X-Request-ID header on all HTTP transactions."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid4())

        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def get_request_id(request: Request) -> str:
    """Retrieve request ID from request state or return a fallback UUID."""
    return getattr(request.state, "request_id", str(uuid4()))


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors cleanly without exposing raw internal details."""
    req_id = get_request_id(request)
    logger.warning("API validation error on request %s: %s", req_id, exc)

    error_body = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Request parameter validation failed",
        request_id=req_id,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_body.model_dump(),
        headers={"X-Request-ID": req_id},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions cleanly with safe error response."""
    req_id = get_request_id(request)
    logger.warning(
        "HTTPException on request %s: status=%d, detail=%s",
        req_id,
        exc.status_code,
        exc.detail,
    )

    code_map = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
    }
    err_code = code_map.get(exc.status_code, "ERROR")

    # Safe message string (never exposing tracebacks or DB URLs)
    safe_msg = str(exc.detail) if isinstance(exc.detail, str) else "Request processing failed"

    error_body = ErrorResponse(
        error_code=err_code,
        message=safe_msg,
        request_id=req_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body.model_dump(),
        headers={"X-Request-ID": req_id},
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Isolate unhandled server exceptions: log traceback, return safe HTTP 500."""
    req_id = get_request_id(request)
    logger.error("Unhandled exception on request %s: %s", req_id, exc, exc_info=True)

    error_body = ErrorResponse(
        error_code="INTERNAL_SERVER_ERROR",
        message="An internal server error occurred",
        request_id=req_id,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_body.model_dump(),
        headers={"X-Request-ID": req_id},
    )
