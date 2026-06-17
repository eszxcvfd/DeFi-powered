"""Tests for the calendar export audit sanitizer contract (US-045)."""

from __future__ import annotations

from livelead.application.calendar_export.service import _payload_sanitized
from livelead.domain.observability.sanitization import sanitize_alert_payload


def test_payload_sanitized_returns_dict_and_flag() -> None:
    cleaned, redacted = _payload_sanitized(
        {
            "scope": "event",
            "event_id": "evt-1",
            "calendar_status": "TENTATIVE",
        }
    )
    assert cleaned["scope"] == "event"
    assert cleaned["event_id"] == "evt-1"
    assert cleaned["calendar_status"] == "TENTATIVE"
    assert redacted is False


def test_payload_sanitized_redacts_sensitive_keys() -> None:
    cleaned, redacted = _payload_sanitized(
        {
            "scope": "watchlist",
            "api_key": "sk-12345",
            "cookie": "session=abc",
            "event_count": 12,
        }
    )
    assert redacted is True
    assert cleaned["scope"] == "watchlist"
    assert cleaned["event_count"] == 12
    assert "api_key" not in cleaned or cleaned["api_key"] == "[REDACTED]"
    assert "cookie" not in cleaned or cleaned["cookie"] == "[REDACTED]"


def test_sanitize_alert_payload_round_trip() -> None:
    cleaned, _ = sanitize_alert_payload({"scope": "event", "count": 5})
    assert cleaned["scope"] == "event"
    assert cleaned["count"] == 5


def test_payload_sanitized_handles_none() -> None:
    cleaned, redacted = _payload_sanitized({"value": None})
    assert cleaned == {"value": None}
    assert redacted is False
