"""In-process login rate limiter (US-027).

The limiter keeps a small sliding window of failed login attempts keyed
by `client_ip + email_hash` so it cannot be used to enumerate emails.
A real deployment should swap this for a Redis-backed limiter; the public
contract here is the same so the call sites do not need to change.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import deque
from dataclasses import dataclass


DEFAULT_THRESHOLD = 5
DEFAULT_WINDOW_SECONDS = 60.0
DEFAULT_LOCKOUT_SECONDS = 15 * 60.0


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    locked_until_ts: float
    failure_count: int
    threshold: int
    lockout_seconds: float

    @property
    def locked_until_seconds_remaining(self) -> float:
        return max(0.0, self.locked_until_ts - time.time())


def make_key(*, email_hash: str, client_ip: str) -> str:
    return f"{email_hash}|{client_ip}"


class LoginRateLimiter:
    def __init__(
        self,
        *,
        threshold: int = DEFAULT_THRESHOLD,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        lockout_seconds: float = DEFAULT_LOCKOUT_SECONDS,
        clock=time.time,
    ) -> None:
        self._threshold = max(1, int(threshold))
        self._window_seconds = max(1.0, float(window_seconds))
        self._lockout_seconds = max(1.0, float(lockout_seconds))
        self._clock = clock
        self._failures: dict[str, deque[float]] = {}
        self._locks: dict[str, float] = {}
        self._mutex = threading.Lock()

    def check(self, *, email_hash: str, client_ip: str) -> RateLimitDecision:
        key = make_key(email_hash=email_hash, client_ip=client_ip)
        now = self._clock()
        with self._mutex:
            locked_until = self._locks.get(key, 0.0)
            if locked_until > now:
                return RateLimitDecision(
                    allowed=False,
                    locked_until_ts=locked_until,
                    failure_count=self._threshold,
                    threshold=self._threshold,
                    lockout_seconds=self._lockout_seconds,
                )
            window = self._failures.get(key)
            if window is not None:
                cutoff = now - self._window_seconds
                while window and window[0] < cutoff:
                    window.popleft()
                if not window:
                    self._failures.pop(key, None)
                    window = None
            failures = len(window) if window else 0
            return RateLimitDecision(
                allowed=True,
                locked_until_ts=0.0,
                failure_count=failures,
                threshold=self._threshold,
                lockout_seconds=self._lockout_seconds,
            )

    def record_failure(self, *, email_hash: str, client_ip: str) -> RateLimitDecision:
        key = make_key(email_hash=email_hash, client_ip=client_ip)
        now = self._clock()
        with self._mutex:
            window = self._failures.setdefault(key, deque())
            window.append(now)
            cutoff = now - self._window_seconds
            while window and window[0] < cutoff:
                window.popleft()
            if not window:
                del self._failures[key]
            failures = len(window) if window else 0
            locked_until = self._locks.get(key, 0.0)
            if failures >= self._threshold:
                locked_until = now + self._lockout_seconds
                self._locks[key] = locked_until
                self._failures.pop(key, None)
            return RateLimitDecision(
                allowed=locked_until <= now,
                locked_until_ts=locked_until,
                failure_count=min(failures, self._threshold),
                threshold=self._threshold,
                lockout_seconds=self._lockout_seconds,
            )

    def record_success(self, *, email_hash: str, client_ip: str) -> None:
        key = make_key(email_hash=email_hash, client_ip=client_ip)
        with self._mutex:
            self._failures.pop(key, None)
            self._locks.pop(key, None)

    def reset(self) -> None:
        with self._mutex:
            self._failures.clear()
            self._locks.clear()


def hash_email_for_limiter(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


__all__ = [
    "DEFAULT_THRESHOLD",
    "DEFAULT_WINDOW_SECONDS",
    "DEFAULT_LOCKOUT_SECONDS",
    "RateLimitDecision",
    "LoginRateLimiter",
    "make_key",
    "hash_email_for_limiter",
]
