import threading
from collections.abc import Callable
from datetime import datetime, timedelta

import pytest
from app.core import clock
from app.core.exceptions import RateLimitedError
from app.core.throttle import LoginThrottle, account_key, normalise_username

START = datetime(2026, 11, 7, 9, 0, 0)
WINDOW = 900
LIMIT = 5
IP = "10.0.0.1"


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
def throttle(advance: Callable[[int], None]) -> LoginThrottle:
    return LoginThrottle(max_failures=LIMIT, window_seconds=WINDOW)


def _fail(throttle: LoginThrottle, times: int, account: str = "id:1", ip: str | None = IP) -> None:
    for _ in range(times):
        throttle.check(account=account)
        throttle.record_failure(account=account, client_ip=ip)


def test_fifth_failure_is_allowed_and_sixth_attempt_is_rejected(throttle: LoginThrottle) -> None:
    _fail(throttle, LIMIT)
    with pytest.raises(RateLimitedError) as info:
        throttle.check(account="id:1")
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
        throttle.check(account="id:1")
    assert info.value.retry_after_seconds == WINDOW - 100


def test_attempts_are_accepted_again_once_the_oldest_failure_leaves_the_window(
    throttle: LoginThrottle, advance: Callable[[int], None]
) -> None:
    _fail(throttle, LIMIT)
    advance(WINDOW - 1)
    with pytest.raises(RateLimitedError) as info:
        throttle.check(account="id:1")
    assert info.value.retry_after_seconds == 1
    advance(WINDOW)
    throttle.check(account="id:1")


def test_account_limit_applies_regardless_of_address(throttle: LoginThrottle) -> None:
    for i in range(LIMIT):
        _fail(throttle, 1, ip=f"10.0.0.{i}")
    with pytest.raises(RateLimitedError):
        throttle.check(account="id:1")
    throttle.check(account="id:2")


def test_address_failures_never_block_the_check_before_verification(
    throttle: LoginThrottle,
) -> None:
    """Five failed guesses from one address must not stop another account's login."""
    for i in range(LIMIT):
        _fail(throttle, 1, account=f"name:guess-{i}")
    throttle.check(account="id:7")
    throttle.record_success(account="id:7")


def test_sixth_failure_from_one_address_is_answered_with_429(throttle: LoginThrottle) -> None:
    for i in range(LIMIT):
        _fail(throttle, 1, account=f"name:guess-{i}")
    throttle.check(account="name:guess-99")
    with pytest.raises(RateLimitedError) as info:
        throttle.record_failure(account="name:guess-99", client_ip=IP)
    assert info.value.retry_after_seconds == WINDOW
    # The failure is still counted against the account and a second address is unaffected.
    throttle.check(account="name:guess-99")
    throttle.record_failure(account="name:guess-99", client_ip="10.0.0.2")


def test_unknown_client_address_skips_the_address_dimension(throttle: LoginThrottle) -> None:
    for i in range(LIMIT + 3):
        _fail(throttle, 1, account=f"name:guess-{i}", ip=None)
    assert throttle.tracked_keys() == LIMIT + 3


def test_success_clears_the_account_but_not_the_address(throttle: LoginThrottle) -> None:
    _fail(throttle, LIMIT - 1)
    throttle.check(account="id:1")
    throttle.record_success(account="id:1")
    # The account starts from zero, but the address already holds four failures.
    _fail(throttle, 1)
    throttle.check(account="id:1")
    with pytest.raises(RateLimitedError):
        throttle.record_failure(account="id:1", client_ip=IP)
    throttle.check(account="id:1")
    throttle.record_failure(account="id:1", client_ip="10.0.0.2")


def test_check_reserves_a_slot_until_the_attempt_is_recorded(throttle: LoginThrottle) -> None:
    for _ in range(LIMIT):
        throttle.check(account="id:1")
    assert throttle.pending_slots() == LIMIT
    with pytest.raises(RateLimitedError) as info:
        throttle.check(account="id:1")
    assert info.value.retry_after_seconds == WINDOW
    throttle.record_success(account="id:1")
    assert throttle.pending_slots() == LIMIT - 1
    throttle.check(account="id:1")


def test_concurrent_checks_cannot_exceed_the_limit(throttle: LoginThrottle) -> None:
    attempts = LIMIT * 4
    barrier = threading.Barrier(attempts)
    outcomes: list[bool] = []
    lock = threading.Lock()

    def attempt() -> None:
        barrier.wait()
        try:
            throttle.check(account="id:1")
            admitted = True
        except RateLimitedError:
            admitted = False
        with lock:
            outcomes.append(admitted)

    threads = [threading.Thread(target=attempt) for _ in range(attempts)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert outcomes.count(True) == LIMIT
    assert outcomes.count(False) == attempts - LIMIT


def test_an_abandoned_reservation_expires_with_the_window(
    throttle: LoginThrottle, advance: Callable[[int], None]
) -> None:
    for _ in range(LIMIT):
        throttle.check(account="id:1")
    advance(WINDOW)
    throttle.check(account="id:1")
    assert throttle.pending_slots() == 1


def test_expired_entries_are_pruned_on_every_call(
    throttle: LoginThrottle, advance: Callable[[int], None]
) -> None:
    _fail(throttle, 2, account="name:a", ip="10.0.0.1")
    _fail(throttle, 1, account="name:b", ip="10.0.0.2")
    assert throttle.tracked_keys() == 4
    advance(WINDOW)
    throttle.check(account="name:unrelated")
    assert throttle.tracked_keys() == 0


def test_reset_forgets_everything(throttle: LoginThrottle) -> None:
    _fail(throttle, LIMIT)
    throttle.check(account="id:2")
    throttle.reset()
    throttle.check(account="id:1")
    assert throttle.tracked_keys() == 0
    assert throttle.pending_slots() == 1


def test_limits_must_be_positive() -> None:
    with pytest.raises(ValueError):
        LoginThrottle(max_failures=0, window_seconds=WINDOW)
    with pytest.raises(ValueError):
        LoginThrottle(max_failures=LIMIT, window_seconds=0)


# The last entry is "ADMIN" in fullwidth letters, which NFKD folds to ASCII.
FULLWIDTH_ADMIN = "\uff21\uff24\uff2d\uff29\uff2e"


@pytest.mark.parametrize(
    "variant", ["admin", "ADMIN", " Admin ", "ädmin", "Ädmin", FULLWIDTH_ADMIN]
)
def test_spelling_variants_of_an_unknown_name_share_one_key(variant: str) -> None:
    assert normalise_username(variant) == "admin"
    assert account_key(variant, None) == "name:admin"


def test_known_users_are_keyed_by_id_whatever_the_spelling() -> None:
    assert account_key("ADMIN", 3) == account_key("ädmin", 3) == "id:3"
    assert account_key("admin", 3) != account_key("admin", None)
