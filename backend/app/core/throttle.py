"""Sliding-window throttle for failed login attempts.

Design
------
Two kinds of key are counted, and they play different roles.

Account key. Before the password is verified, ``check`` looks at the account
key alone. Once it holds ``max_failures`` failures (or reserved slots, see
below) inside ``window_seconds``, every further attempt for that account is
rejected with 429 until the oldest failure leaves the window. This is the real
lockout. ``account_key`` builds the key from the user id when the username
matched a row and from a normalised username otherwise (NFKD, combining marks
removed, casefolded), so ``ADMIN`` and ``ädmin`` count against ``admin`` and an
attacker cannot buy extra attempts by varying the spelling.

Address key. The client address is counted only when a verification has
already failed, in ``record_failure``. When the address has already used up
its ``max_failures`` failures inside the window the failed attempt is answered
with 429 instead of 401. A correct password is never blocked because of the
address alone, so one shared address (every browser behind the Vite dev proxy
arrives from 127.0.0.1) cannot lock other users out. The address is still
useful: a guessing run that walks through usernames gets 429 after a handful
of attempts, and the per-account lockout above applies to each name it tries.
When the server does not know the peer address (``request.client`` is None)
the address dimension is skipped.

Reservation. ``check`` reserves a pending slot for the account under the
lock, and ``record_failure`` or ``record_success`` converts or releases it.
Concurrent requests for one account therefore cannot exceed the limit by all
passing ``check`` before any of them records. A slot that is never resolved
(a crash between the two calls) expires with the window.

Storage. The store is a plain dictionary in the memory of one API process,
guarded by a lock. It is enough for the single-process deployment this
project runs; several workers or several hosts would each keep their own
counts and would need a shared store (for example a table or Redis) to
enforce one limit. Expired timestamps are pruned on every call, so memory is
bounded by the number of distinct keys that failed inside the current window.

Time comes from ``app.core.clock`` so tests can pin it without sleeping.
"""

import logging
import math
import threading
import unicodedata
from collections import deque
from datetime import datetime, timedelta
from functools import lru_cache

from app.core import clock
from app.core.config import get_settings
from app.core.exceptions import RateLimitedError

logger = logging.getLogger(__name__)

_Bucket = dict[str, deque[datetime]]


class LoginThrottle:
    def __init__(self, *, max_failures: int, window_seconds: int) -> None:
        if max_failures < 1 or window_seconds < 1:
            raise ValueError("max_failures and window_seconds must be positive")
        self._max_failures = max_failures
        self._window = timedelta(seconds=window_seconds)
        self._lock = threading.Lock()
        self._by_account: _Bucket = {}
        self._pending: _Bucket = {}
        self._by_ip: _Bucket = {}

    def check(self, *, account: str) -> None:
        """Reserve a slot for the account, or reject the attempt before any password work."""
        with self._lock:
            now = clock.now()
            self._prune(now)
            failures = self._by_account.get(account, deque())
            pending = self._pending.get(account, deque())
            if len(failures) + len(pending) >= self._max_failures:
                retry_after = self._retry_after(failures, pending, now)
            else:
                retry_after = 0
                self._pending.setdefault(account, deque()).append(now)
        if retry_after > 0:
            self._reject("account", retry_after)

    def record_failure(self, *, account: str, client_ip: str | None) -> None:
        """Convert the reservation into a failure; 429 when the address is over its limit."""
        with self._lock:
            now = clock.now()
            self._prune(now)
            self._release_locked(account)
            self._by_account.setdefault(account, deque()).append(now)
            retry_after = 0
            if client_ip is not None:
                stamps = self._by_ip.setdefault(client_ip, deque())
                stamps.append(now)
                if len(stamps) > self._max_failures:
                    retry_after = self._retry_after(stamps, deque(), now)
        if retry_after > 0:
            self._reject("address", retry_after)

    def record_success(self, *, account: str) -> None:
        """Forget the account's failures; the address keeps its own count."""
        with self._lock:
            self._release_locked(account)
            self._by_account.pop(account, None)
            self._prune(clock.now())

    def reset(self) -> None:
        with self._lock:
            self._by_account.clear()
            self._pending.clear()
            self._by_ip.clear()

    def tracked_keys(self) -> int:
        """Number of keys currently holding at least one failure (for tests)."""
        with self._lock:
            return len(self._by_account) + len(self._by_ip)

    def pending_slots(self) -> int:
        """Number of reservations not yet converted or released (for tests)."""
        with self._lock:
            return sum(len(stamps) for stamps in self._pending.values())

    def _release_locked(self, account: str) -> None:
        pending = self._pending.get(account)
        if pending:
            pending.popleft()
        if not pending:
            self._pending.pop(account, None)

    def _prune(self, now: datetime) -> None:
        cutoff = now - self._window
        for bucket in (self._by_account, self._pending, self._by_ip):
            for key in list(bucket):
                stamps = bucket[key]
                while stamps and stamps[0] <= cutoff:
                    stamps.popleft()
                if not stamps:
                    del bucket[key]

    def _retry_after(
        self, failures: deque[datetime], pending: deque[datetime], now: datetime
    ) -> int:
        """Seconds until the oldest counted entry expires, at least one."""
        oldest = min(stamps[0] for stamps in (failures, pending) if stamps)
        remaining = (oldest + self._window - now).total_seconds()
        return max(1, math.ceil(remaining))

    @staticmethod
    def _reject(dimension: str, retry_after: int) -> None:
        logger.warning(
            "login throttled by %s",
            dimension,
            extra={
                "operation": "login",
                "status": 429,
                "error": "RateLimitedError",
                "retry_after_seconds": retry_after,
            },
        )
        raise RateLimitedError(retry_after_seconds=retry_after)


def account_key(username: str, user_id: int | None) -> str:
    """Key for the account bucket: the user id when known, else the normalised username."""
    if user_id is not None:
        return f"id:{user_id}"
    return f"name:{normalise_username(username)}"


def normalise_username(username: str) -> str:
    """Fold case and accents so spelling variants of one name share a bucket."""
    decomposed = unicodedata.normalize("NFKD", username.strip())
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.casefold()


@lru_cache
def get_login_throttle() -> LoginThrottle:
    settings = get_settings()
    return LoginThrottle(
        max_failures=settings.login_max_failures, window_seconds=settings.login_window_seconds
    )
