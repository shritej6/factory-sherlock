"""Login throttling through the real endpoint.

Starlette's ``TestClient`` reports every request as coming from the address
``testclient``, so the default client exercises the per-address counter as
well as the per-account counter. A second ``TestClient`` with a different
``client`` tuple stands in for another machine.
"""

from app.api.routes.auth import _client_ip
from app.core.config import get_settings
from app.core.throttle import get_login_throttle
from app.main import app
from fastapi import Request
from fastapi.testclient import TestClient
from httpx import Response

from tests.conftest import TEST_PASSWORD

LOGIN = "/api/v1/auth/login"


def _login(client: TestClient, username: str, password: str) -> Response:
    return client.post(LOGIN, json={"username": username, "password": password})


def _exhaust(client: TestClient, username: str) -> None:
    for _ in range(get_settings().login_max_failures):
        assert _login(client, username, "wrong-password").status_code == 401


def _other_machine() -> TestClient:
    return TestClient(app, client=("203.0.113.9", 40000))


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


def test_correct_password_is_also_rejected_while_the_account_is_locked(
    client: TestClient,
) -> None:
    _exhaust(client, "engineer")
    assert _login(client, "engineer", TEST_PASSWORD).status_code == 429
    assert _login(_other_machine(), "engineer", TEST_PASSWORD).status_code == 429


def test_correct_password_is_accepted_after_reset(client: TestClient) -> None:
    _exhaust(client, "engineer")
    assert _login(client, "engineer", TEST_PASSWORD).status_code == 429
    get_login_throttle().reset()
    assert _login(client, "engineer", TEST_PASSWORD).status_code == 200


def test_failures_as_one_user_do_not_lock_another_user_from_the_same_address(
    client: TestClient,
) -> None:
    """Behind the Vite dev proxy every browser shares 127.0.0.1; B must still get in."""
    _exhaust(client, "engineer")
    assert _login(client, "operator", TEST_PASSWORD).status_code == 200
    assert _login(client, "viewer", TEST_PASSWORD).status_code == 200


def test_sixth_failed_attempt_from_one_address_is_a_429_even_for_a_fresh_name(
    client: TestClient,
) -> None:
    for i in range(get_settings().login_max_failures):
        assert _login(client, f"guess-{i}", "wrong-password").status_code == 401
    blocked = _login(client, "guess-99", "wrong-password")
    assert blocked.status_code == 429
    assert blocked.json()["details"]["retry_after_seconds"] >= 1
    # Another address is unaffected, and the same address can still log in correctly.
    assert _login(_other_machine(), "guess-99", "wrong-password").status_code == 401
    assert _login(client, "operator", TEST_PASSWORD).status_code == 200


def test_unknown_usernames_are_throttled_like_real_ones(client: TestClient) -> None:
    _exhaust(client, "ghost")
    blocked = _login(_other_machine(), "ghost", "wrong-password")
    assert blocked.status_code == 429
    assert blocked.json()["message"] == "Too many failed login attempts. Try again later."


def test_case_and_accent_variants_count_against_the_same_account(client: TestClient) -> None:
    limit = get_settings().login_max_failures
    variants = ["ADMIN", "ädmin", "Admin", "ÄDMIN", "admin"]
    for username in variants[:limit]:
        assert _login(client, username, "wrong-password").status_code == 401
    # Checked from another address so the account counter, not the address, decides.
    assert _login(_other_machine(), "admin", TEST_PASSWORD).status_code == 429


def test_variants_of_an_unknown_username_share_one_bucket(client: TestClient) -> None:
    limit = get_settings().login_max_failures
    variants = ["GHOST", "ghöst", "Ghost", "ghost ", "ghost"]
    for username in variants[:limit]:
        assert _login(client, username, "wrong-password").status_code == 401
    assert _login(_other_machine(), "ghost", "wrong-password").status_code == 429


def test_success_resets_the_account_counter_but_not_the_address_counter(
    client: TestClient,
) -> None:
    limit = get_settings().login_max_failures
    for _ in range(limit - 1):
        assert _login(client, "engineer", "wrong-password").status_code == 401
    assert _login(client, "engineer", TEST_PASSWORD).status_code == 200
    # The account starts from zero; this is the address's fifth failure.
    assert _login(client, "engineer", "wrong-password").status_code == 401
    # The sixth failure from the address is answered with 429, a correct password is not.
    assert _login(client, "engineer", "wrong-password").status_code == 429
    assert _login(client, "viewer", TEST_PASSWORD).status_code == 200


def test_missing_peer_address_is_reported_as_none() -> None:
    scope = {"type": "http", "method": "POST", "path": LOGIN, "headers": []}
    assert _client_ip(Request(scope)) is None
    scope["client"] = ("198.51.100.4", 5000)
    assert _client_ip(Request(scope)) == "198.51.100.4"
