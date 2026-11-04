from fastapi.testclient import TestClient

from tests.conftest import TEST_PASSWORD


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
