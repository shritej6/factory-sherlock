"""Maps application and database errors to safe HTTP responses.

Clients never see SQL text, stack traces, or driver messages. Everything is
logged server-side with the request id for diagnosis, and the same id is
returned to the client so a user can quote it when reporting a problem.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

from app.api.request_id import REQUEST_ID_HEADER, request_id_of
from app.core.exceptions import AppError, RateLimitedError

logger = logging.getLogger(__name__)

MYSQL_DUPLICATE_KEY = 1062
MYSQL_FK_VIOLATION = 1452
MYSQL_RETRYABLE = frozenset({1205, 1213})  # lock wait timeout, deadlock


def _mysql_error_code(exc: IntegrityError | OperationalError) -> int | None:
    args = getattr(exc.orig, "args", ())
    return args[0] if args and isinstance(args[0], int) else None


def _response(
    request: Request,
    status: int,
    error: str,
    message: str,
    details: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = request_id_of(request)
    return JSONResponse(
        status_code=status,
        headers={REQUEST_ID_HEADER: request_id, **(headers or {})},
        content={
            "error": error,
            "message": message,
            "details": details or {},
            "request_id": request_id,
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.info(
            "request rejected",
            extra={
                "request_id": request_id_of(request),
                "operation": f"{request.method} {request.url.path}",
                "error": type(exc).__name__,
                "status": exc.status_code,
            },
        )
        headers = (
            {"Retry-After": str(exc.retry_after_seconds)}
            if isinstance(exc, RateLimitedError)
            else None
        )
        return _response(
            request, exc.status_code, type(exc).__name__, exc.message, exc.details, headers
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return _response(
            request, 422, "ValidationError", "Request failed validation", {"errors": errors}
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity(request: Request, exc: IntegrityError) -> JSONResponse:
        code = _mysql_error_code(exc)
        request_id = request_id_of(request)
        if code == MYSQL_DUPLICATE_KEY:
            logger.warning("duplicate key", extra={"request_id": request_id}, exc_info=exc)
            return _response(
                request, 409, "ConflictError", "The request duplicates an existing record"
            )
        if code == MYSQL_FK_VIOLATION:
            logger.warning("foreign key violation", extra={"request_id": request_id}, exc_info=exc)
            return _response(
                request, 422, "ValidationError", "The request references a row that does not exist"
            )
        # Anything else (NOT NULL, CHECK, data too long) is a server-side bug.
        logger.error("integrity error", extra={"request_id": request_id}, exc_info=exc)
        return _response(request, 500, "InternalError", "The request violated a database rule")

    @app.exception_handler(OperationalError)
    async def handle_operational(request: Request, exc: OperationalError) -> JSONResponse:
        request_id = request_id_of(request)
        if _mysql_error_code(exc) in MYSQL_RETRYABLE:
            logger.warning("lock contention", extra={"request_id": request_id}, exc_info=exc)
            return _response(
                request, 409, "ConflictError", "Another request changed the same rows; retry"
            )
        logger.error("database unavailable", extra={"request_id": request_id}, exc_info=exc)
        return _response(request, 503, "DatabaseUnavailable", "The database is not reachable")

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", extra={"request_id": request_id_of(request)})
        return _response(request, 500, "InternalError", "An unexpected error occurred")
