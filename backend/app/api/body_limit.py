"""Rejects request bodies over a size cap before authentication and parsing.

Pure ASGI, so no request object is built and no body is read into memory: a
declared ``Content-Length`` above the cap is answered with 413 before the
route runs, and a chunked body is counted as it streams and aborted with 413
once it passes the cap. The cap is per route: the CSV import accepts its
1 MiB file plus multipart framing, every other route a 64 KiB JSON document.
The response has the standard error body; ``request_id`` comes from the
request id middleware, which wraps this one.
"""

import json
import logging

from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.request_id import REQUEST_ID_HEADER
from app.services.inspection_csv import MAX_FILE_BYTES

logger = logging.getLogger(__name__)

KIB = 1024
DEFAULT_BODY_LIMIT = 64 * KIB
IMPORT_BODY_LIMIT = MAX_FILE_BYTES + 64 * KIB
IMPORT_PATH = "/api/v1/inspections/import"
ERROR_CODE = "payload_too_large"


class PayloadTooLarge(HTTPException):
    """Raised by the counting receive once a streamed body passes the cap.

    It is an ``HTTPException`` because FastAPI re-raises those unchanged while
    reading the body and turns every other exception into a 400.
    """

    def __init__(self, limit: int) -> None:
        super().__init__(status_code=413, detail="Request body is too large")
        self.limit = limit


class _ResponseReplacedError(Exception):
    """The 413 was sent in place of the response the application started."""


def body_limit_for(scope: Scope) -> int:
    if scope.get("method") == "POST" and scope.get("path") == IMPORT_PATH:
        return IMPORT_BODY_LIMIT
    return DEFAULT_BODY_LIMIT


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = body_limit_for(scope)
        declared = _content_length(scope)
        if declared is not None and declared > limit:
            await _send_too_large(scope, send, limit)
            return
        await _LimitedRequest(self.app, scope, receive, send, limit).run()


class _LimitedRequest:
    """Counts the streamed body of one request and aborts it past the cap."""

    def __init__(
        self, app: ASGIApp, scope: Scope, receive: Receive, send: Send, limit: int
    ) -> None:
        self.app = app
        self.scope = scope
        self._receive = receive
        self._send = send
        self.limit = limit
        self.received = 0
        self.exceeded = False
        self.response_started = False

    async def run(self) -> None:
        try:
            await self.app(self.scope, self.receive, self.send)
        except PayloadTooLarge:
            if self.response_started:
                raise
            await _send_too_large(self.scope, self._send, self.limit)
        except _ResponseReplacedError:
            pass

    async def receive(self) -> Message:
        message = await self._receive()
        if message["type"] == "http.request":
            self.received += len(message.get("body", b""))
            if self.received > self.limit:
                self.exceeded = True
                raise PayloadTooLarge(self.limit)
        return message

    async def send(self, message: Message) -> None:
        if message["type"] == "http.response.start":
            if self.exceeded:
                # The application's own error response (FastAPI's HTTPException
                # handler) is replaced by the standard body.
                await _send_too_large(self.scope, self._send, self.limit)
                raise _ResponseReplacedError
            self.response_started = True
        await self._send(message)


def _content_length(scope: Scope) -> int | None:
    value = Headers(scope=scope).get("content-length")
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


async def _send_too_large(scope: Scope, send: Send, limit: int) -> None:
    request_id = str(scope.get("state", {}).get("request_id", "unknown"))
    logger.info(
        "request rejected",
        extra={
            "request_id": request_id,
            "operation": f"{scope.get('method')} {scope.get('path')}",
            "error": ERROR_CODE,
            "status": 413,
        },
    )
    message = f"The request body is larger than the {limit // KIB} KiB limit for this route"
    body = json.dumps(
        {
            "error": ERROR_CODE,
            "message": message,
            "details": {"limit_bytes": limit},
            "request_id": request_id,
        }
    ).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
        (REQUEST_ID_HEADER.lower().encode("ascii"), request_id.encode("ascii")),
    ]
    await send({"type": "http.response.start", "status": 413, "headers": headers})
    await send({"type": "http.response.body", "body": body})
