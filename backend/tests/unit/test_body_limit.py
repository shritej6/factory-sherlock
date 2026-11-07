"""BodySizeLimitMiddleware on a small application: no database involved."""

import asyncio
import json
from typing import Annotated

from app.api.body_limit import (
    DEFAULT_BODY_LIMIT,
    IMPORT_BODY_LIMIT,
    IMPORT_PATH,
    BodySizeLimitMiddleware,
)
from app.api.request_id import request_id_middleware
from fastapi import FastAPI, File, UploadFile
from fastapi.testclient import TestClient
from httpx import Response
from starlette.types import Message, Receive, Scope, Send


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware)
    app.middleware("http")(request_id_middleware)

    @app.post(IMPORT_PATH)
    async def import_route(file: Annotated[UploadFile, File()]) -> dict[str, int]:
        return {"size": len(await file.read())}

    @app.post("/echo")
    async def echo(body: dict[str, int]) -> dict[str, int]:
        return body

    @app.get("/ping")
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    return app


def _assert_too_large(response: Response, limit: int) -> None:
    assert response.status_code == 413, response.text
    body = response.json()
    assert set(body) == {"error", "message", "details", "request_id"}
    assert body["error"] == "payload_too_large"
    assert body["details"] == {"limit_bytes": limit}
    assert f"{limit // 1024} KiB" in body["message"]
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert len(body["request_id"]) == 12


def test_declared_oversized_json_body_is_rejected_with_the_default_cap() -> None:
    client = TestClient(_app())
    response = client.post(
        "/echo",
        content=b"x" * (DEFAULT_BODY_LIMIT + 1),
        headers={"Content-Type": "application/json"},
    )
    _assert_too_large(response, DEFAULT_BODY_LIMIT)


def test_import_route_accepts_a_full_size_file_and_rejects_more() -> None:
    client = TestClient(_app())
    file = b"x" * (IMPORT_BODY_LIMIT - 64 * 1024)
    accepted = client.post(IMPORT_PATH, files={"file": ("big.csv", file, "text/csv")})
    assert accepted.status_code == 200 and accepted.json() == {"size": len(file)}
    rejected = client.post(
        IMPORT_PATH,
        content=b"x" * (IMPORT_BODY_LIMIT + 1),
        headers={"Content-Type": "multipart/form-data; boundary=b"},
    )
    _assert_too_large(rejected, IMPORT_BODY_LIMIT)
    # The larger cap belongs to the import path only.
    elsewhere = client.post(
        "/echo",
        content=b"x" * (IMPORT_BODY_LIMIT - 64 * 1024),
        headers={"Content-Type": "application/json"},
    )
    _assert_too_large(elsewhere, DEFAULT_BODY_LIMIT)


def test_chunked_oversized_body_is_rejected_while_streaming() -> None:
    client = TestClient(_app())
    chunks = (b"x" * 40_000 for _ in range(2))
    response = client.post("/echo", content=chunks, headers={"Content-Type": "application/json"})
    assert "content-length" not in response.request.headers
    _assert_too_large(response, DEFAULT_BODY_LIMIT)


def test_normal_bodies_and_bodiless_requests_pass() -> None:
    client = TestClient(_app())
    assert client.post("/echo", json={"a": 1}).json() == {"a": 1}
    assert client.get("/ping").json() == {"ok": True}
    small = client.post(IMPORT_PATH, files={"file": ("s.csv", b"a,b\n", "text/csv")})
    assert small.status_code == 200 and small.json() == {"size": 4}


def test_streamed_chunks_are_counted_and_the_application_is_cut_off() -> None:
    """ASGI level: three 30 KB chunks pass the 64 KiB cap on the third message."""
    reads = 0
    finished = False

    async def reading_app(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal reads, finished
        while True:
            reads += 1
            if not (await receive()).get("more_body", False):
                break
        finished = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"done"})

    messages: list[Message] = [
        {"type": "http.request", "body": b"x" * 30_000, "more_body": True} for _ in range(3)
    ]
    messages.append({"type": "http.request", "body": b""})
    sent: list[Message] = []

    async def receive() -> Message:
        return messages.pop(0)

    async def send(message: Message) -> None:
        sent.append(message)

    scope: Scope = {"type": "http", "method": "POST", "path": "/echo", "headers": []}
    asyncio.run(BodySizeLimitMiddleware(reading_app)(scope, receive, send))
    assert (reads, finished) == (3, False)
    assert [m["type"] for m in sent] == ["http.response.start", "http.response.body"]
    assert sent[0]["status"] == 413
    assert json.loads(sent[1]["body"])["details"] == {"limit_bytes": DEFAULT_BODY_LIMIT}
