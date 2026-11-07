"""Login throttling through the real endpoint.

Starlette's ``TestClient`` reports every request as coming from the address
``testclient``, so the default client exercises the per-address counter as
well as the per-username counter. A second ``TestClient`` with a different
``client`` tuple stands in for another machine.
"""

from app.core.config import get_settings
from app.core.throttle import get_login_throttle
from app.main import app
from fastapi.testclient import TestClient
from httpx import Response

from tests.conftest import TEST_PASSWORD

LOGIN = "/api/v1/auth/login"


def _login(client: TestClient, username: str, password: str) -> Response:
    return client.post(LOGIN, json={"username": username, "password": password})


def _exhaust(client: TestClient, username: str) -> None:
    for _ in range(get_settings().login_max_failures):
        assert _login(client, username, "wrong-password").status_code == 401


def test_sixth_attempt_returns_429_with_retry_after(client: TestClient) -> None:
    _exhaust(client, "engineer")
    blocked = _login(client, "engineer", "wrong-password")
    assert blocked.status_code == 429
    body = blocked.json()
    retry_after = body["details"]["retry_after_seconds"]
    assert body["error"] == "RateLimitedError"
    assert body["message"] == "Too many failed login attempts. Try again later."
    assert 1 <= retry_after <= get_settings().login_window_seconds
    assert blocked.headers["Retry-After"] == str(retry_after)
    assert body["request_id"] == blocked.headers["X-Request-ID"]
    assert set(body) == {"error", "message", "details", "request_id"}


def test_correct_password_is_also_rejected_while_locked(client: TestClient) -> None:
    _exhaust(client, "engineer")
    assert _login(client, "engineer", TEST_PASSWORD).status_code == 429


def test_correct_password_is_accepted_after_reset(client: TestClient) -> None:
    _exhaust(client, "engineer")
    assert _login(client, "engineer", TEST_PASSWORD).status_code == 429
    get_login_throttle().reset()
    assert _login(client, "engineer", TEST_PASSWORD).status_code == 200


def test_lock_on_one_username_does_not_block_another_from_a_different_address(
    client: TestClient,
) -> None:
    _exhaust(client, "engineer")
    other_machine = TestClient(app, client=("203.0.113.9", 40000))
    # Different username, different address: unaffected.
    assert _login(other_machine, "operator", TEST_PASSWORD).status_code == 200
    # Same username from elsewhere: still locked, the username counter is global.
    assert _login(other_machine, "engineer", TEST_PASSWORD).status_code == 429
    # Different username from the exhausted address: locked by the address counter.
    assert _login(client, "operator", TEST_PASSWORD).status_code == 429


def test_unknown_usernames_are_throttled_like_real_ones(client: TestClient) -> None:
    _exhaust(client, "ghost")
    blocked = _login(client, "ghost", "wrong-password")
    assert blocked.status_code == 429
    assert blocked.json()["message"] == "Too many failed login attempts. Try again later."


def test_success_resets_the_username_counter_but_not_the_address_counter(
    client: TestClient,
) -> None:
    limit = get_settings().login_max_failures
    for _ in range(limit - 1):
        assert _login(client, "engineer", "wrong-password").status_code == 401
    assert _login(client, "engineer", TEST_PASSWORD).status_code == 200
    # The username starts from zero, so this failure is accepted and checked,
    # but it is the address's fifth failure and locks the address.
    assert _login(client, "engineer", "wrong-password").status_code == 401
    assert _login(client, "engineer", "wrong-password").status_code == 429
    assert _login(client, "viewer", TEST_PASSWORD).status_code == 429
