"""Sliding-window throttle for failed login attempts.

Failures are counted per lowercase username and per client address. Once a
key reaches ``max_failures`` inside ``window_seconds``, further attempts for
that key are rejected until its oldest failure leaves the window. A
successful login clears the username's failures but not the address's, so a
guessing run that happens to hit one valid password stays slowed down.

The store is a plain dictionary in the memory of one API process, guarded by
a lock. It is enough for the single-process deployment this project runs;
several workers or several hosts would each keep their own counts and would
need a shared store (for example a table or Redis) to enforce one limit.
Expired timestamps are pruned on every call, so memory is bounded by the
number of distinct keys that failed inside the current window.

Time comes from ``app.core.clock`` so tests can pin it without sleeping.
"""

import logging
import math
import threading
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
        self._by_user: _Bucket = {}
        self._by_ip: _Bucket = {}

    def check(self, *, username: str, client_ip: str) -> None:
        """Reject the attempt before any password work when either key is over the limit."""
        with self._lock:
            now = clock.now()
            self._prune(now)
            retry_after = max(
                self._retry_after(self._by_user, _user_key(username), now),
                self._retry_after(self._by_ip, client_ip, now),
            )
        if retry_after > 0:
            logger.warning(
                "login throttled",
                extra={"operation": "login", "retry_after_seconds": retry_after},
            )
            raise RateLimitedError(retry_after_seconds=retry_after)

    def record_failure(self, *, username: str, client_ip: str) -> None:
        with self._lock:
            now = clock.now()
            self._prune(now)
            self._by_user.setdefault(_user_key(username), deque()).append(now)
            self._by_ip.setdefault(client_ip, deque()).append(now)

    def record_success(self, *, username: str) -> None:
        """Forget the username's failures; the address keeps its own count."""
        with self._lock:
            self._by_user.pop(_user_key(username), None)
            self._prune(clock.now())

    def reset(self) -> None:
        with self._lock:
            self._by_user.clear()
            self._by_ip.clear()

    def tracked_keys(self) -> int:
        """Number of keys currently holding at least one failure (for tests)."""
        with self._lock:
            return len(self._by_user) + len(self._by_ip)

    def _prune(self, now: datetime) -> None:
        cutoff = now - self._window
        for bucket in (self._by_user, self._by_ip):
            for key in list(bucket):
                stamps = bucket[key]
                while stamps and stamps[0] <= cutoff:
                    stamps.popleft()
                if not stamps:
                    del bucket[key]

    def _retry_after(self, bucket: _Bucket, key: str, now: datetime) -> int:
        """Seconds until the oldest failure expires, or 0 when the key is under the limit."""
        stamps = bucket.get(key)
        if stamps is None or len(stamps) < self._max_failures:
            return 0
        remaining = (stamps[0] + self._window - now).total_seconds()
        return max(1, math.ceil(remaining))


def _user_key(username: str) -> str:
    return username.strip().lower()


@lru_cache
def get_login_throttle() -> LoginThrottle:
    settings = get_settings()
    return LoginThrottle(
        max_failures=settings.login_max_failures, window_seconds=settings.login_window_seconds
    )
