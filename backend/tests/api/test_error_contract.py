"""The error contract of app.api.errors: every failure path returns the same body shape.

The 500 and 503 paths cannot be reached with ordinary requests, so a service
function is replaced for one request (500) or the session factory is pointed
at a port where nothing listens (503). The checks are the ones a client relies
on: the documented keys, the request id in body and header, and the absence of
exception text, SQL, driver names, and stack traces.
"""

import pymysql
import pytest
from app.core import database
from app.main import app
from app.services import analytics_service, catalog_service
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import create_engine
from sqlalchemy.exc import DataError, IntegrityError, OperationalError, TimeoutError
from sqlalchemy.orm import Session, sessionmaker

ERROR_KEYS = {"error", "message", "details", "request_id"}
LEAK_MARKERS = ("Traceback", "SELECT", "pymysql", "sqlalchemy", "secret-detail-7f3a")
UNREACHABLE_URL = "mysql+pymysql://nobody:nothing@127.0.0.1:1/none?connect_timeout=1"


@pytest.fixture
def tolerant_client(db_session: Session) -> TestClient:
    """A client that returns 500 responses instead of re-raising server exceptions."""
    return TestClient(app, raise_server_exceptions=False)


def _assert_safe_error_body(response: Response, status: int, error: str) -> dict[str, object]:
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == ERROR_KEYS
    assert body["error"] == error
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert len(body["request_id"]) == 12
    for marker in LEAK_MARKERS:
        assert marker not in response.text
    return body


def test_unexpected_exception_returns_a_generic_500_with_request_id(
    tolerant_client: TestClient, engineer: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(session: Session) -> list[object]:
        raise RuntimeError("secret-detail-7f3a: this text must never reach the client")

    monkeypatch.setattr(catalog_service, "list_machines", explode)
    response = tolerant_client.get("/api/v1/machines", headers=engineer)
    body = _assert_safe_error_body(response, 500, "InternalError")
    assert body["message"] == "An unexpected error occurred"
    assert body["details"] == {}
    assert "RuntimeError" not in response.text


def test_database_unavailable_returns_503_for_health_and_protected_routes(
    client: TestClient, engineer: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    unreachable = sessionmaker(bind=create_engine(UNREACHABLE_URL), autoflush=False)
    monkeypatch.setattr(database, "SessionLocal", unreachable)

    health = client.get("/api/v1/health")
    body = _assert_safe_error_body(health, 503, "DatabaseUnavailable")
    assert body["message"] == "The database is not reachable"
    assert body["details"] == {}
    assert "Can't connect" not in health.text

    protected = client.get("/api/v1/machines", headers=engineer)
    _assert_safe_error_body(protected, 503, "DatabaseUnavailable")


def _raise_operational(code: int, message: str = "Deadlock found when trying to get lock"):  # type: ignore[no-untyped-def]
    def fail(*args: object, **kwargs: object) -> object:
        raise OperationalError(
            "UPDATE production_orders SET quantity_completed = 1",
            {},
            pymysql.err.OperationalError(code, message),
        )

    return fail


def _raise_data(code: int):  # type: ignore[no-untyped-def]
    def fail(*args: object, **kwargs: object) -> object:
        raise DataError(
            "INSERT INTO inspections (serial_number) VALUES ('x')",
            {},
            pymysql.err.DataError(code, "Data too long for column 'serial_number' at row 1"),
        )

    return fail


def _raise_pool_timeout(*args: object, **kwargs: object) -> object:
    raise TimeoutError("QueuePool limit of size 5 overflow 10 reached")


def _raise_integrity(code: int):  # type: ignore[no-untyped-def]
    def fail(*args: object, **kwargs: object) -> object:
        raise IntegrityError(
            "INSERT INTO inspections (unit_id) VALUES (1)",
            {},
            pymysql.err.IntegrityError(code, "Cannot add or update a child row"),
        )

    return fail


@pytest.mark.parametrize("code", [1205, 1213])
def test_lock_contention_is_reported_as_a_retryable_409(
    client: TestClient, engineer: dict[str, str], monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    monkeypatch.setattr(analytics_service, "recent_alerts", _raise_operational(code))
    response = client.get("/api/v1/analytics/alerts", headers=engineer)
    body = _assert_safe_error_body(response, 409, "ConflictError")
    assert "retry" in str(body["message"])
    assert "Deadlock" not in response.text


def test_foreign_key_violation_from_the_database_is_a_422(
    client: TestClient, engineer: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(analytics_service, "recent_alerts", _raise_integrity(1452))
    response = client.get("/api/v1/analytics/alerts", headers=engineer)
    body = _assert_safe_error_body(response, 422, "ValidationError")
    assert body["message"] == "The request references a row that does not exist"


def test_other_integrity_errors_are_server_errors_without_detail(
    tolerant_client: TestClient, engineer: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(analytics_service, "recent_alerts", _raise_integrity(1048))
    response = tolerant_client.get("/api/v1/analytics/alerts", headers=engineer)
    body = _assert_safe_error_body(response, 500, "InternalError")
    assert body["message"] == "The request violated a database rule"
    assert "child row" not in response.text


def test_every_client_error_body_has_the_documented_keys_and_no_internals(
    client: TestClient, engineer: dict[str, str], viewer: dict[str, str]
) -> None:
    product = {"code": "DUP-PRODUCT", "name": "Duplicate"}
    assert client.post("/api/v1/products", json=product, headers=engineer).status_code == 201
    responses = {
        401: client.get("/api/v1/machines"),
        403: client.post("/api/v1/machines", json={"code": "CNC-09", "name": "X"}, headers=viewer),
        404: client.get("/api/v1/production-orders/999999", headers=engineer),
        409: client.post("/api/v1/products", json=product, headers=engineer),
        422: client.post(
            "/api/v1/machines", json={"code": "bad code", "name": ""}, headers=engineer
        ),
    }
    expected_errors = {
        401: "AuthenticationError",
        403: "AuthorizationError",
        404: "NotFoundError",
        409: "ConflictError",
        422: "ValidationError",
    }
    for status, response in responses.items():
        _assert_safe_error_body(response, status, expected_errors[status])


def test_check_constraint_violation_from_the_database_is_a_422_with_the_constraint_name(
    client: TestClient, engineer: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        analytics_service,
        "recent_alerts",
        _raise_operational(3819, "Check constraint 'chk_alerts_severity' is violated."),
    )
    response = client.get("/api/v1/analytics/alerts", headers=engineer)
    body = _assert_safe_error_body(response, 422, "ValidationError")
    assert body["message"] == "A database check constraint rejected the change"
    assert body["details"] == {"constraint": "chk_alerts_severity"}


def test_data_too_long_is_a_422_and_other_data_errors_are_generic_500s(
    tolerant_client: TestClient, engineer: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(analytics_service, "recent_alerts", _raise_data(1406))
    response = tolerant_client.get("/api/v1/analytics/alerts", headers=engineer)
    body = _assert_safe_error_body(response, 422, "ValidationError")
    assert body["message"] == "A value is too long for its column"
    assert "serial_number" not in response.text

    monkeypatch.setattr(analytics_service, "recent_alerts", _raise_data(1366))
    response = tolerant_client.get("/api/v1/analytics/alerts", headers=engineer)
    body = _assert_safe_error_body(response, 500, "InternalError")
    assert body["message"] == "An unexpected error occurred"


def test_other_operational_errors_are_503_unavailable_and_pool_timeouts_not_reachable(
    client: TestClient, engineer: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        analytics_service, "recent_alerts", _raise_operational(1040, "Too many connections")
    )
    response = client.get("/api/v1/analytics/alerts", headers=engineer)
    body = _assert_safe_error_body(response, 503, "DatabaseUnavailable")
    assert body["message"] == "The database is unavailable"
    assert "Too many connections" not in response.text

    monkeypatch.setattr(analytics_service, "recent_alerts", _raise_pool_timeout)
    response = client.get("/api/v1/analytics/alerts", headers=engineer)
    body = _assert_safe_error_body(response, 503, "DatabaseUnavailable")
    assert body["message"] == "The database is not reachable"
    assert "QueuePool" not in response.text
