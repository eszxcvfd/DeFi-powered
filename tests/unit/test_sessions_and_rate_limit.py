"""Session token and rate-limit helpers (US-027)."""

from __future__ import annotations

import time

import pytest

from livelead.domain.identity import (
    LoginFailureReason,
    LoginRateLimiter,
    SESSION_TOKEN_BYTES,
    constant_time_eq,
    generate_session_token,
    hash_email_for_limiter,
    hash_session_token,
)


def test_generate_session_token_is_url_safe_and_unique():
    a = generate_session_token()
    b = generate_session_token()
    assert a != b
    # URL-safe base64 alphabet, no padding required.
    assert all(ch.isalnum() or ch in "-_" for ch in a)
    assert len(a) >= 32  # 32 bytes encoded as urlsafe


def test_hash_session_token_is_deterministic_and_different_per_token():
    a = generate_session_token()
    b = generate_session_token()
    h1 = hash_session_token(a)
    h2 = hash_session_token(a)
    h3 = hash_session_token(b)
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64  # sha256 hex


def test_hash_session_token_rejects_empty():
    with pytest.raises(ValueError):
        hash_session_token("")


def test_constant_time_eq_returns_true_for_same_string():
    assert constant_time_eq("abc", "abc") is True
    assert constant_time_eq("", "") is True
    assert constant_time_eq("abc", "abd") is False
    assert constant_time_eq("abc", "ab") is False


def test_rate_limiter_blocks_after_threshold():
    limiter = LoginRateLimiter(threshold=2, window_seconds=60, lockout_seconds=10)
    key = hash_email_for_limiter("a@example.com")
    decision = limiter.check(email_hash=key, client_ip="1.1.1.1")
    assert decision.allowed is True
    d1 = limiter.record_failure(email_hash=key, client_ip="1.1.1.1")
    d2 = limiter.record_failure(email_hash=key, client_ip="1.1.1.1")
    assert d2.allowed is False
    assert d2.locked_until_seconds_remaining > 0
    decision_after = limiter.check(email_hash=key, client_ip="1.1.1.1")
    assert decision_after.allowed is False


def test_rate_limiter_success_clears_window():
    limiter = LoginRateLimiter(threshold=3, window_seconds=60, lockout_seconds=5)
    key = hash_email_for_limiter("b@example.com")
    limiter.record_failure(email_hash=key, client_ip="1.1.1.1")
    limiter.record_failure(email_hash=key, client_ip="1.1.1.1")
    limiter.record_success(email_hash=key, client_ip="1.1.1.1")
    decision = limiter.check(email_hash=key, client_ip="1.1.1.1")
    assert decision.failure_count == 0


def test_rate_limiter_window_drops_old_failures():
    fake_now = {"t": 1000.0}

    def clock() -> float:
        return fake_now["t"]

    limiter = LoginRateLimiter(threshold=2, window_seconds=10, lockout_seconds=5, clock=clock)
    key = hash_email_for_limiter("c@example.com")
    limiter.record_failure(email_hash=key, client_ip="1.1.1.1")
    fake_now["t"] = 1015.0  # window has moved past the first failure
    decision = limiter.check(email_hash=key, client_ip="1.1.1.1")
    assert decision.failure_count == 0


def test_rate_limiter_keys_dont_collide_across_ips():
    limiter = LoginRateLimiter(threshold=1, window_seconds=60, lockout_seconds=5)
    key = hash_email_for_limiter("d@example.com")
    limiter.record_failure(email_hash=key, client_ip="1.1.1.1")
    decision_other = limiter.check(email_hash=key, client_ip="2.2.2.2")
    assert decision_other.allowed is True
    decision_same = limiter.check(email_hash=key, client_ip="1.1.1.1")
    assert decision_same.allowed is False


def test_login_failure_reason_values():
    assert LoginFailureReason.INVALID_CREDENTIALS == "invalid_credentials"
    assert LoginFailureReason.LOCKED == "locked"
    assert LoginFailureReason.RATE_LIMITED == "rate_limited"
    assert LoginFailureReason.DISABLED == "disabled"
    assert LoginFailureReason.UNKNOWN == "unknown"
