"""Maps application and database errors to safe HTTP responses.

Clients never see SQL text, stack traces, or driver messages. Everything is
logged server-side with the request id for diagnosis, and the same id is
returned to the client so a user can quote it when reporting a problem.

The ``classify_*`` functions hold the mapping from a driver error to a status
and message and are pure, so the table below can be unit tested without a
request. The handlers only add logging and the response envelope.
"""

import logging
import re
from dataclasses import dataclass, field

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, IntegrityError, OperationalError, TimeoutError

from app.api.request_id import REQUEST_ID_HEADER, request_id_of
from app.core.exceptions import AppError, RateLimitedError

logger = logging.getLogger(__name__)

MYSQL_DUPLICATE_KEY = 1062
MYSQL_FK_VIOLATION = 1452
MYSQL_DATA_TOO_LONG = 1406
MYSQL_CHECK_VIOLATION = 3819
MYSQL_RETRYABLE = frozenset({1205, 1213})  # lock wait timeout, deadlock
# Client-side connection errors: server gone, cannot connect, lost connection.
MYSQL_UNREACHABLE = frozenset({2002, 2003, 2006, 2013})

_CHECK_NAME = re.compile(r"Check constraint '([^']+)' is violated")


@dataclass(frozen=True)
class ErrorMapping:
    status: int
    error: str
    message: str
    details: dict[str, object] = field(default_factory=dict)
    log_level: int = logging.ERROR
    log_message: str = "database error"


def _driver_args(exc: Exception) -> tuple[object, ...]:
    """The (errno, message) pair pymysql attaches to the wrapped driver error."""
    orig = getattr(exc, "orig", None)
    args = getattr(orig, "args", ())
    return tuple(args) if isinstance(args, tuple) else ()


def mysql_error_code(exc: Exception) -> int | None:
    args = _driver_args(exc)
    return args[0] if args and isinstance(args[0], int) else None


def _mysql_message(exc: Exception) -> str:
    args = _driver_args(exc)
    return str(args[1]) if len(args) > 1 else ""


def classify_integrity(exc: IntegrityError) -> ErrorMapping:
    code = mysql_error_code(exc)
    if code == MYSQL_DUPLICATE_KEY:
        return ErrorMapping(
            409,
            "ConflictError",
            "The request duplicates an existing record",
            log_level=logging.WARNING,
            log_message="duplicate key",
        )
    if code == MYSQL_FK_VIOLATION:
        return ErrorMapping(
            422,
            "ValidationError",
            "The request references a row that does not exist",
            log_level=logging.WARNING,
            log_message="foreign key violation",
        )
    # Anything else (NOT NULL and friends) is a server-side bug.
    return ErrorMapping(
        500, "InternalError", "The request violated a database rule", log_message="integrity error"
    )


def classify_operational(exc: OperationalError | TimeoutError) -> ErrorMapping:
    code = mysql_error_code(exc)
    if code in MYSQL_RETRYABLE:
        return ErrorMapping(
            409,
            "ConflictError",
            "Another request changed the same rows; retry",
            log_level=logging.WARNING,
            log_message="lock contention",
        )
    if code == MYSQL_CHECK_VIOLATION:
        match = _CHECK_NAME.search(_mysql_message(exc))
        details: dict[str, object] = {"constraint": match.group(1)} if match else {}
        return ErrorMapping(
            422,
            "ValidationError",
            "A database check constraint rejected the change",
            details,
            log_level=logging.WARNING,
            log_message="check constraint violation",
        )
    if code in MYSQL_UNREACHABLE or isinstance(exc, TimeoutError):
        return ErrorMapping(
            503,
            "DatabaseUnavailable",
            "The database is not reachable",
            log_message="database unreachable",
        )
    return ErrorMapping(
        503, "DatabaseUnavailable", "The database is unavailable", log_message="database error"
    )


def classify_data(exc: DataError) -> ErrorMapping:
    if mysql_error_code(exc) == MYSQL_DATA_TOO_LONG:
        return ErrorMapping(
            422,
            "ValidationError",
            "A value is too long for its column",
            log_level=logging.WARNING,
            log_message="data too long",
        )
    return ErrorMapping(
        500, "InternalError", "An unexpected error occurred", log_message="data error"
    )


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


def _mapped_response(request: Request, exc: Exception, mapping: ErrorMapping) -> JSONResponse:
    logger.log(
        mapping.log_level,
        mapping.log_message,
        extra={"request_id": request_id_of(request), "status": mapping.status},
        exc_info=exc,
    )
    return _response(request, mapping.status, mapping.error, mapping.message, mapping.details)


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
        {"Retry-After": str(exc.retry_after_seconds)} if isinstance(exc, RateLimitedError) else None
    )
    return _response(
        request, exc.status_code, type(exc).__name__, exc.message, exc.details, headers
    )


async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()
    ]
    return _response(
        request, 422, "ValidationError", "Request failed validation", {"errors": errors}
    )


async def handle_integrity(request: Request, exc: IntegrityError) -> JSONResponse:
    return _mapped_response(request, exc, classify_integrity(exc))


async def handle_operational(
    request: Request, exc: OperationalError | TimeoutError
) -> JSONResponse:
    return _mapped_response(request, exc, classify_operational(exc))


async def handle_data(request: Request, exc: DataError) -> JSONResponse:
    return _mapped_response(request, exc, classify_data(exc))


async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error", extra={"request_id": request_id_of(request)})
    return _response(request, 500, "InternalError", "An unexpected error occurred")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, handle_validation)  # type: ignore[arg-type]
    app.add_exception_handler(IntegrityError, handle_integrity)  # type: ignore[arg-type]
    app.add_exception_handler(OperationalError, handle_operational)  # type: ignore[arg-type]
    app.add_exception_handler(TimeoutError, handle_operational)  # type: ignore[arg-type]
    app.add_exception_handler(DataError, handle_data)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, handle_unexpected)
