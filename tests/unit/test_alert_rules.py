"""Unit tests for the alert rule validation and the sanitization helper."""

from __future__ import annotations

import pytest

from livelead.domain.observability.enums import (
    AlertChannel,
    AlertMetric,
    AlertOperator,
    AlertSeverity,
)
from livelead.domain.observability.models import (
    AlertEvent,
    AlertRule,
    evaluate_threshold,
    hash_dedup_key,
    validate_rule_payload,
)
from livelead.domain.observability.sanitization import sanitize_alert_payload


# ---------------------------------------------------------------------------
# validate_rule_payload
# ---------------------------------------------------------------------------


def test_validate_rule_payload_accepts_valid_critical_rule() -> None:
    validate_rule_payload(
        name="backup.stale",
        metric=AlertMetric.BACKUP_AGE_HOURS,
        operator=AlertOperator.GT,
        threshold=26.0,
        window_seconds=0,
        severity=AlertSeverity.CRITICAL,
        channels=[AlertChannel.IN_APP, AlertChannel.EMAIL],
        cooldown_seconds=3600,
    )


def test_validate_rule_payload_rejects_unknown_metric() -> None:
    with pytest.raises(ValueError, match="ALERT_RULE_INVALID:metric_unsupported"):
        validate_rule_payload(
            name="x",
            metric="not.a.metric",
            operator=AlertOperator.GT,
            threshold=1.0,
            window_seconds=0,
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.IN_APP],
            cooldown_seconds=600,
        )


def test_validate_rule_payload_rejects_unknown_operator() -> None:
    with pytest.raises(ValueError, match="ALERT_RULE_INVALID:operator_unsupported"):
        validate_rule_payload(
            name="x",
            metric=AlertMetric.BACKUP_AGE_HOURS,
            operator="!=",
            threshold=1.0,
            window_seconds=0,
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.IN_APP],
            cooldown_seconds=600,
        )


def test_validate_rule_payload_rejects_unknown_severity() -> None:
    with pytest.raises(ValueError, match="ALERT_RULE_INVALID:severity_unsupported"):
        validate_rule_payload(
            name="x",
            metric=AlertMetric.BACKUP_AGE_HOURS,
            operator=AlertOperator.GT,
            threshold=1.0,
            window_seconds=0,
            severity="fatal",
            channels=[AlertChannel.IN_APP],
            cooldown_seconds=600,
        )


def test_validate_rule_payload_rejects_unknown_channel() -> None:
    with pytest.raises(ValueError, match="ALERT_RULE_INVALID:channel_unsupported"):
        validate_rule_payload(
            name="x",
            metric=AlertMetric.BACKUP_AGE_HOURS,
            operator=AlertOperator.GT,
            threshold=1.0,
            window_seconds=0,
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.IN_APP, "pager"],
            cooldown_seconds=600,
        )


def test_validate_rule_payload_rejects_empty_channels() -> None:
    with pytest.raises(ValueError, match="ALERT_RULE_INVALID:channels_required"):
        validate_rule_payload(
            name="x",
            metric=AlertMetric.BACKUP_AGE_HOURS,
            operator=AlertOperator.GT,
            threshold=1.0,
            window_seconds=0,
            severity=AlertSeverity.WARNING,
            channels=[],
            cooldown_seconds=600,
        )


def test_validate_rule_payload_rejects_nan_threshold() -> None:
    with pytest.raises(ValueError, match="ALERT_RULE_INVALID:threshold_nan"):
        validate_rule_payload(
            name="x",
            metric=AlertMetric.BACKUP_AGE_HOURS,
            operator=AlertOperator.GT,
            threshold=float("nan"),
            window_seconds=0,
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.IN_APP],
            cooldown_seconds=600,
        )


def test_validate_rule_payload_rejects_oversized_window() -> None:
    with pytest.raises(ValueError, match="ALERT_RULE_INVALID:window_out_of_range"):
        validate_rule_payload(
            name="x",
            metric=AlertMetric.BACKUP_AGE_HOURS,
            operator=AlertOperator.GT,
            threshold=1.0,
            window_seconds=10**9,
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.IN_APP],
            cooldown_seconds=600,
        )


def test_validate_rule_payload_rejects_oversized_cooldown() -> None:
    with pytest.raises(ValueError, match="ALERT_RULE_INVALID:cooldown_out_of_range"):
        validate_rule_payload(
            name="x",
            metric=AlertMetric.BACKUP_AGE_HOURS,
            operator=AlertOperator.GT,
            threshold=1.0,
            window_seconds=0,
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.IN_APP],
            cooldown_seconds=10**9,
        )


def test_validate_rule_payload_rejects_blank_name() -> None:
    with pytest.raises(ValueError, match="ALERT_RULE_INVALID:name_required"):
        validate_rule_payload(
            name="   ",
            metric=AlertMetric.BACKUP_AGE_HOURS,
            operator=AlertOperator.GT,
            threshold=1.0,
            window_seconds=0,
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.IN_APP],
            cooldown_seconds=600,
        )


# ---------------------------------------------------------------------------
# evaluate_threshold
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "operator,value,threshold,expected",
    [
        (AlertOperator.GT, 27.0, 26.0, True),
        (AlertOperator.GT, 26.0, 26.0, False),
        (AlertOperator.GTE, 26.0, 26.0, True),
        (AlertOperator.LT, 25.0, 26.0, True),
        (AlertOperator.LT, 26.0, 26.0, False),
        (AlertOperator.LTE, 26.0, 26.0, True),
        (AlertOperator.EQ, 26.0, 26.0, True),
        (AlertOperator.EQ, 25.0, 26.0, False),
        (AlertOperator.GT, float("inf"), 26.0, True),
    ],
)
def test_evaluate_threshold_grammar(operator, value, threshold, expected) -> None:
    assert evaluate_threshold(operator, value, threshold) is expected


# ---------------------------------------------------------------------------
# sanitize_alert_payload
# ---------------------------------------------------------------------------


def test_sanitize_alert_payload_strips_api_key() -> None:
    payload = {"api_key": "sk-1234567890abcdef", "rule_name": "test"}
    cleaned, redacted = sanitize_alert_payload(payload)
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["rule_name"] == "test"
    assert redacted is True


def test_sanitize_alert_payload_strips_jwt() -> None:
    payload = {"token": "eyJabc.def.ghi"}
    cleaned, redacted = sanitize_alert_payload(payload)
    assert cleaned["token"] == "[REDACTED_JWT]" or cleaned["token"] == "[REDACTED]"
    assert redacted is True


def test_sanitize_alert_payload_keeps_safe_payload() -> None:
    payload = {"rule_name": "test", "value": 42, "details": {"count": 1}}
    cleaned, redacted = sanitize_alert_payload(payload)
    assert cleaned == payload
    assert redacted is False


def test_sanitize_alert_payload_handles_none() -> None:
    cleaned, redacted = sanitize_alert_payload(None)
    assert cleaned == {}
    assert redacted is False


def test_sanitize_alert_payload_handles_non_dict() -> None:
    cleaned, redacted = sanitize_alert_payload("hello")
    assert cleaned == {"value": "hello"}
    assert redacted is False


# ---------------------------------------------------------------------------
# dedup
# ---------------------------------------------------------------------------


def test_dedup_bucket_changes_with_cooldown() -> None:
    rule = AlertRule(
        id="rule-1",
        organization_id="org-1",
        name="r",
        metric=AlertMetric.BACKUP_AGE_HOURS,
        operator=AlertOperator.GT,
        threshold=0.0,
        cooldown_seconds=600,
        channels=(AlertChannel.IN_APP,),
    )
    from datetime import datetime, UTC

    t1 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 1, 1, 0, 11, 0, tzinfo=UTC)
    assert rule.dedup_bucket(t1) == rule.dedup_bucket(t1)
    assert rule.dedup_bucket(t1) != rule.dedup_bucket(t2)


def test_hash_dedup_key_is_deterministic() -> None:
    assert hash_dedup_key("rule-1", "abc") == hash_dedup_key("rule-1", "abc")
    assert hash_dedup_key("rule-1", "abc") != hash_dedup_key("rule-1", "xyz")
