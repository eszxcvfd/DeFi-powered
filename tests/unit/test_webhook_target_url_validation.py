"""Tests for the webhook target URL validation (US-049)."""

from __future__ import annotations

from livelead.application.webhooks.target_url import (
    validate_target_url,
)
from livelead.domain.webhooks.models import (
    WebhookDeliveryThresholds,
)


THRESHOLDS = WebhookDeliveryThresholds()


def test_validate_https_url_is_valid() -> None:
    ok, reason = validate_target_url(
        "https://siem.example.com/webhook",
        thresholds=THRESHOLDS,
    )
    assert ok is True
    assert reason == ""


def test_validate_http_localhost_is_valid() -> None:
    ok, reason = validate_target_url(
        "http://localhost:8000/webhook",
        thresholds=THRESHOLDS,
    )
    assert ok is True


def test_validate_http_non_localhost_is_invalid() -> None:
    ok, reason = validate_target_url(
        "http://siem.example.com/webhook",
        thresholds=THRESHOLDS,
    )
    assert ok is False
    assert reason == "WEBHOOK_TARGET_URL_HTTP_NOT_LOCALHOST"


def test_validate_metadata_service_is_invalid() -> None:
    ok, reason = validate_target_url(
        "https://169.254.169.254/webhook",
        thresholds=THRESHOLDS,
    )
    assert ok is False
    assert reason == "WEBHOOK_TARGET_URL_METADATA_BLOCKED"


def test_validate_private_ip_is_invalid() -> None:
    ok, reason = validate_target_url(
        "https://10.0.0.1/webhook",
        thresholds=THRESHOLDS,
    )
    assert ok is False
    assert reason == "WEBHOOK_TARGET_URL_PRIVATE_BLOCKED"


def test_validate_rfc1918_ip_is_invalid() -> None:
    ok, reason = validate_target_url(
        "https://192.168.1.1/webhook",
        thresholds=THRESHOLDS,
    )
    assert ok is False
    assert reason == "WEBHOOK_TARGET_URL_PRIVATE_BLOCKED"


def test_validate_loopback_ip_is_invalid() -> None:
    ok, reason = validate_target_url(
        "https://127.0.0.1/webhook",
        thresholds=THRESHOLDS,
    )
    assert ok is False
    assert reason == "WEBHOOK_TARGET_URL_PRIVATE_BLOCKED"


def test_validate_invalid_scheme_is_invalid() -> None:
    ok, reason = validate_target_url(
        "ftp://siem.example.com/webhook",
        thresholds=THRESHOLDS,
    )
    assert ok is False
    assert reason == "WEBHOOK_TARGET_URL_SCHEME_INVALID"


def test_validate_empty_url_is_invalid() -> None:
    ok, reason = validate_target_url("", thresholds=THRESHOLDS)
    assert ok is False
    assert reason == "WEBHOOK_TARGET_URL_INVALID"


def test_validate_too_long_url_is_invalid() -> None:
    long_url = "https://siem.example.com/" + "a" * 2100
    ok, reason = validate_target_url(long_url, thresholds=THRESHOLDS)
    assert ok is False
    assert reason == "WEBHOOK_TARGET_URL_TOO_LONG"


def test_validate_ipv6_loopback_is_invalid() -> None:
    ok, reason = validate_target_url(
        "https://[::1]/webhook",
        thresholds=THRESHOLDS,
    )
    assert ok is False
    assert reason == "WEBHOOK_TARGET_URL_PRIVATE_BLOCKED"
