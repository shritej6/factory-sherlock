"""Request body caps on the real application: 413 before authentication, with a request id."""

from app.api.body_limit import DEFAULT_BODY_LIMIT, IMPORT_BODY_LIMIT
from fastapi.testclient import TestClient
from httpx import Response

IMPORT_URL = "/api/v1/inspections/import"
LOGIN_URL = "/api/v1/auth/login"


def _assert_too_large(response: Response, limit: int) -> None:
    assert response.status_code == 413, response.text
    body = response.json()
    assert body["error"] == "payload_too_large"
    assert body["details"] == {"limit_bytes": limit}
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert len(body["request_id"]) == 12


def test_oversized_import_upload_is_rejected_before_authentication(client: TestClient) -> None:
    response = client.post(
        IMPORT_URL,
        content=b"x" * (IMPORT_BODY_LIMIT + 1),
        headers={"Content-Type": "multipart/form-data; boundary=b"},
    )
    _assert_too_large(response, IMPORT_BODY_LIMIT)


def test_oversized_json_body_is_rejected_on_an_ordinary_route(client: TestClient) -> None:
    padding = "x" * (DEFAULT_BODY_LIMIT + 1)
    response = client.post(LOGIN_URL, json={"username": "operator", "password": padding})
    _assert_too_large(response, DEFAULT_BODY_LIMIT)


def test_chunked_oversized_body_is_rejected(client: TestClient) -> None:
    chunks = (b"x" * 40_000 for _ in range(2))
    response = client.post(LOGIN_URL, content=chunks, headers={"Content-Type": "application/json"})
    assert "content-length" not in response.request.headers
    _assert_too_large(response, DEFAULT_BODY_LIMIT)


def test_normal_bodies_pass_the_cap(client: TestClient, operator: dict[str, str]) -> None:
    """Login succeeded for the fixture; an import under the cap reaches row validation."""
    text = "serial_number,characteristic,measured_value\nS1,diameter,20.0\n"
    response = client.post(
        IMPORT_URL, files={"file": ("m.csv", text.encode(), "text/csv")}, headers=operator
    )
    assert response.status_code == 422
    assert response.json()["details"]["errors"][0]["field"] == "serial_number"
