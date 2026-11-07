from collections.abc import Callable
from datetime import datetime, timedelta

import pytest
from app.core import clock
from app.core.exceptions import RateLimitedError
from app.core.throttle import LoginThrottle

START = datetime(2026, 11, 7, 9, 0, 0)
WINDOW = 900
LIMIT = 5


@pytest.fixture
def advance(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], None]:
    """Pins ``clock.now`` to START and returns a function that moves it forward."""
    current = START

    def fake_now() -> datetime:
        return current

    def move(seconds: int) -> None:
        nonlocal current
        current = START + timedelta(seconds=seconds)

    monkeypatch.setattr(clock, "now", fake_now)
    return move


@pytest.fixture
def throttle() -> LoginThrottle:
    return LoginThrottle(max_failures=LIMIT, window_seconds=WINDOW)


def _fail(
    throttle: LoginThrottle, times: int, user: str = "engineer", ip: str = "10.0.0.1"
) -> None:
    for _ in range(times):
        throttle.check(username=user, client_ip=ip)
        throttle.record_failure(username=user, client_ip=ip)


def test_fifth_failure_is_allowed_and_sixth_attempt_is_rejected(
    throttle: LoginThrottle, advance: Callable[[int], None]
) -> None:
    _fail(throttle, LIMIT)
    with pytest.raises(RateLimitedError) as info:
        throttle.check(username="engineer", client_ip="10.0.0.1")
    assert info.value.status_code == 429
    assert info.value.message == "Too many failed login attempts. Try again later."
    assert info.value.details == {"retry_after_seconds": WINDOW}
    assert info.value.retry_after_seconds == WINDOW


def test_retry_after_counts_down_from_the_oldest_failure(
    throttle: LoginThrottle, advance: Callable[[int], None]
) -> None:
    for i in range(LIMIT):
        advance(i * 10)
        _fail(throttle, 1)
    advance(100)
    with pytest.raises(RateLimitedError) as info:
        throttle.check(username="engineer", client_ip="10.0.0.1")
    assert info.value.retry_after_seconds == WINDOW - 100


def test_attempts_are_accepted_again_once_the_oldest_failure_leaves_the_window(
    throttle: LoginThrottle, advance: Callable[[int], None]
) -> None:
    _fail(throttle, LIMIT)
    advance(WINDOW - 1)
    with pytest.raises(RateLimitedError) as info:
        throttle.check(username="engineer", client_ip="10.0.0.1")
    assert info.value.retry_after_seconds == 1
    advance(WINDOW)
    throttle.check(username="engineer", client_ip="10.0.0.1")


def test_success_clears_the_username_but_not_the_address(
    throttle: LoginThrottle, advance: Callable[[int], None]
) -> None:
    _fail(throttle, LIMIT - 1)
    throttle.record_success(username="engineer")
    # The username can fail four more times, but the address already holds four.
    _fail(throttle, 1)
    with pytest.raises(RateLimitedError):
        throttle.check(username="engineer", client_ip="10.0.0.1")
    with pytest.raises(RateLimitedError):
        throttle.check(username="someone-else", client_ip="10.0.0.1")
    throttle.check(username="engineer", client_ip="10.0.0.2")


def test_address_limit_applies_across_usernames(
    throttle: LoginThrottle, advance: Callable[[int], None]
) -> None:
    for i in range(LIMIT):
        _fail(throttle, 1, user=f"guess-{i}")
    with pytest.raises(RateLimitedError):
        throttle.check(username="guess-99", client_ip="10.0.0.1")
    throttle.check(username="guess-99", client_ip="10.0.0.2")


def test_username_limit_applies_across_addresses_and_ignores_case(
    throttle: LoginThrottle, advance: Callable[[int], None]
) -> None:
    for i in range(LIMIT):
        _fail(throttle, 1, user="Engineer " if i % 2 else "engineer", ip=f"10.0.0.{i}")
    with pytest.raises(RateLimitedError):
        throttle.check(username="ENGINEER", client_ip="10.0.0.200")
    throttle.check(username="operator", client_ip="10.0.0.200")


def test_expired_entries_are_pruned_on_every_call(
    throttle: LoginThrottle, advance: Callable[[int], None]
) -> None:
    _fail(throttle, 2, user="a", ip="10.0.0.1")
    _fail(throttle, 1, user="b", ip="10.0.0.2")
    assert throttle.tracked_keys() == 4
    advance(WINDOW)
    throttle.check(username="unrelated", client_ip="10.0.0.9")
    assert throttle.tracked_keys() == 0


def test_reset_forgets_everything(throttle: LoginThrottle, advance: Callable[[int], None]) -> None:
    _fail(throttle, LIMIT)
    throttle.reset()
    throttle.check(username="engineer", client_ip="10.0.0.1")
    assert throttle.tracked_keys() == 0


def test_limits_must_be_positive() -> None:
    with pytest.raises(ValueError):
        LoginThrottle(max_failures=0, window_seconds=WINDOW)
    with pytest.raises(ValueError):
        LoginThrottle(max_failures=LIMIT, window_seconds=0)
