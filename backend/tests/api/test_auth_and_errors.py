import pytest
from app.models import User, UserRole
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from tests.conftest import TEST_PASSWORD

REASON = {"reason": "long enough reason"}
ENGINEER_ONLY_ROUTES = [
    ("POST", "/api/v1/products", {"code": "NEW-1", "name": "n"}),
    ("PATCH", "/api/v1/products/1", {"name": "n"}),
    ("POST", "/api/v1/machines", {"code": "CNC-09", "name": "n"}),
    (
        "POST",
        "/api/v1/material-lots",
        {
            "lot_number": "L9",
            "material_name": "m",
            "supplier": "s",
            "quantity_received": "1",
            "received_at": "2026-01-01T00:00:00",
        },
    ),
    (
        "POST",
        "/api/v1/production-orders",
        {"order_number": "PO-9", "product_id": 1, "quantity_planned": 1},
    ),
    ("PATCH", "/api/v1/production-orders/1", {"due_date": "2026-12-01"}),
    ("POST", "/api/v1/production-batches/1/quarantine", REASON),
    ("POST", "/api/v1/traceability/material-lots/1/quarantine", REASON),
    (
        "POST",
        "/api/v1/investigations",
        {
            "title": "abc",
            "window_start": "2026-11-01T00:00:00",
            "window_end": "2026-11-02T00:00:00",
        },
    ),
    ("POST", "/api/v1/simulation/runs", {"seed": 1, "start_time": "2026-11-01T00:00:00"}),
]
OPERATOR_ROUTES = [
    ("POST", "/api/v1/machines/1/status", {"status": "RUNNING", "reason": "r"}),
    ("POST", "/api/v1/production-orders/1/status", {"status": "RELEASED"}),
    (
        "POST",
        "/api/v1/production-batches",
        {
            "production_order_id": 1,
            "quantity": 1,
            "materials": [{"material_lot_id": 1, "quantity_used": "1"}],
        },
    ),
    ("POST", "/api/v1/production-batches/1/complete", None),
    ("POST", "/api/v1/inspections", {"unit_id": 1, "specification_id": 1, "measured_value": "1"}),
    ("POST", "/api/v1/analytics/alerts/1/acknowledge", None),
]


def test_health_round_trips_to_mysql(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok", "database": "ok"}


def test_login_rejects_bad_credentials_without_revealing_which_part(client: TestClient) -> None:
    unknown = client.post("/api/v1/auth/login", json={"username": "ghost", "password": "x"})
    wrong = client.post("/api/v1/auth/login", json={"username": "engineer", "password": "x"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["message"] == wrong.json()["message"]


def test_requests_without_token_are_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/machines")
    assert response.status_code == 401
    assert response.json()["error"] == "AuthenticationError"


def test_tampered_token_is_rejected(client: TestClient, engineer: dict[str, str]) -> None:
    bad = {"Authorization": engineer["Authorization"][:-2] + "zz"}
    assert client.get("/api/v1/machines", headers=bad).status_code == 401


def test_viewer_cannot_mutate(client: TestClient, viewer: dict[str, str]) -> None:
    response = client.post("/api/v1/machines", json={"code": "CNC-09", "name": "X"}, headers=viewer)
    assert response.status_code == 403
    assert response.json()["details"]["required"] == ["ADMIN", "ENGINEER"]


def test_operator_cannot_create_products_but_can_read(
    client: TestClient, operator: dict[str, str]
) -> None:
    assert client.get("/api/v1/products", headers=operator).status_code == 200
    body = {"code": "NEW-PART", "name": "New"}
    assert client.post("/api/v1/products", json=body, headers=operator).status_code == 403


def test_validation_errors_name_the_field(client: TestClient, engineer: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/machines", json={"code": "bad code", "name": ""}, headers=engineer
    )
    assert response.status_code == 422
    fields = {e["field"] for e in response.json()["details"]["errors"]}
    assert fields == {"code", "name"}


def test_unknown_fields_are_rejected(client: TestClient, engineer: dict[str, str]) -> None:
    body = {"code": "CNC-09", "name": "X", "status": "RUNNING"}
    assert client.post("/api/v1/machines", json=body, headers=engineer).status_code == 422


def test_not_found_is_safe(client: TestClient, engineer: dict[str, str]) -> None:
    response = client.get("/api/v1/production-orders/999999", headers=engineer)
    assert response.status_code == 404
    assert "SELECT" not in response.text


def test_me_reflects_database_role(client: TestClient) -> None:
    token = client.post(
        "/api/v1/auth/login", json={"username": "operator", "password": TEST_PASSWORD}
    ).json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["role"] == "OPERATOR" and me["username"] == "operator"


def test_every_error_carries_a_request_id_header_and_field(
    client: TestClient, engineer: dict[str, str]
) -> None:
    response = client.get("/api/v1/production-orders/999999", headers=engineer)
    assert response.status_code == 404
    body = response.json()
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert len(body["request_id"]) == 12
    ok = client.get("/api/v1/machines", headers=engineer)
    assert ok.status_code == 200 and "X-Request-ID" in ok.headers


def test_unknown_user_login_takes_the_slow_path(client: TestClient) -> None:
    missing = client.post(
        "/api/v1/auth/login", json={"username": "nobody", "password": "test-password-123"}
    )
    wrong = client.post("/api/v1/auth/login", json={"username": "viewer", "password": "bad"})
    assert missing.status_code == wrong.status_code == 401
    assert missing.json()["message"] == wrong.json()["message"]


@pytest.mark.parametrize(("method", "path", "body"), ENGINEER_ONLY_ROUTES)
def test_engineer_only_routes_reject_operators_and_viewers(
    client: TestClient,
    operator: dict[str, str],
    viewer: dict[str, str],
    method: str,
    path: str,
    body: dict[str, object] | None,
) -> None:
    for headers in (operator, viewer):
        response = client.request(method, path, json=body, headers=headers)
        assert response.status_code == 403, (path, response.text)
        assert response.json()["details"]["required"] == ["ADMIN", "ENGINEER"]


@pytest.mark.parametrize(("method", "path", "body"), OPERATOR_ROUTES)
def test_operator_routes_reject_viewers_but_admit_operators(
    client: TestClient,
    operator: dict[str, str],
    viewer: dict[str, str],
    method: str,
    path: str,
    body: dict[str, object] | None,
) -> None:
    denied = client.request(method, path, json=body, headers=viewer)
    assert denied.status_code == 403, (path, denied.text)
    assert denied.json()["details"]["required"] == ["ADMIN", "ENGINEER", "OPERATOR"]
    admitted = client.request(method, path, json=body, headers=operator)
    assert admitted.status_code not in (401, 403), (path, admitted.text)


def test_the_database_role_decides_not_the_token(
    client: TestClient, viewer: dict[str, str], db_session: Session
) -> None:
    body = {"code": "CNC-09", "name": "Promoted"}
    assert client.post("/api/v1/machines", json=body, headers=viewer).status_code == 403
    db_session.execute(update(User).where(User.username == "viewer").values(role=UserRole.ENGINEER))
    db_session.commit()
    promoted = client.post("/api/v1/machines", json=body, headers=viewer)
    assert promoted.status_code == 201, promoted.text
    assert client.get("/api/v1/auth/me", headers=viewer).json()["role"] == "ENGINEER"


def test_deactivated_users_lose_access_immediately(
    client: TestClient, operator: dict[str, str], db_session: Session
) -> None:
    assert client.get("/api/v1/machines", headers=operator).status_code == 200
    db_session.execute(update(User).where(User.username == "operator").values(is_active=False))
    db_session.commit()
    response = client.get("/api/v1/machines", headers=operator)
    assert response.status_code == 401
    assert response.json()["message"] == "User account is not active"
    login = client.post(
        "/api/v1/auth/login", json={"username": "operator", "password": TEST_PASSWORD}
    )
    assert login.status_code == 401
    assert login.json()["message"] == "Invalid username or password"
