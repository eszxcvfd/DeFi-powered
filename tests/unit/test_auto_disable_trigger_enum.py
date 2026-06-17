"""Tests for the connector auto-disable enums (US-048)."""

from __future__ import annotations

from livelead.domain.auto_disable.enums import (
    AutoDisableEventStatus,
    AutoDisableTrigger,
)


def test_auto_disable_trigger_is_closed() -> None:
    assert set(AutoDisableTrigger) == {
        AutoDisableTrigger.HEALTH_UNHEALTHY,
        AutoDisableTrigger.CAPTCHA_RATE_BREACH,
        AutoDisableTrigger.FAILURE_RATE_BREACH,
        AutoDisableTrigger.NEEDS_USER_ACTION_STORM,
        AutoDisableTrigger.ERROR_SPIKE,
        AutoDisableTrigger.MANUAL_KILL_SWITCH,
    }


def test_auto_disable_trigger_values_are_stable_strings() -> None:
    assert AutoDisableTrigger.HEALTH_UNHEALTHY.value == "health_unhealthy"
    assert (
        AutoDisableTrigger.CAPTCHA_RATE_BREACH.value
        == "captcha_rate_breach"
    )
    assert (
        AutoDisableTrigger.FAILURE_RATE_BREACH.value
        == "failure_rate_breach"
    )
    assert (
        AutoDisableTrigger.NEEDS_USER_ACTION_STORM.value
        == "needs_user_action_storm"
    )
    assert AutoDisableTrigger.ERROR_SPIKE.value == "error_spike"
    assert (
        AutoDisableTrigger.MANUAL_KILL_SWITCH.value
        == "manual_kill_switch"
    )


def test_auto_disable_event_status_is_closed() -> None:
    assert set(AutoDisableEventStatus) == {
        AutoDisableEventStatus.ACTIVE,
        AutoDisableEventStatus.RECOVERING,
        AutoDisableEventStatus.RESOLVED,
        AutoDisableEventStatus.SUPERSEDED,
    }


def test_auto_disable_event_status_values_are_stable_strings() -> None:
    assert AutoDisableEventStatus.ACTIVE.value == "active"
    assert AutoDisableEventStatus.RECOVERING.value == "recovering"
    assert AutoDisableEventStatus.RESOLVED.value == "resolved"
    assert AutoDisableEventStatus.SUPERSEDED.value == "superseded"


def test_auto_disable_trigger_round_trip() -> None:
    for trigger in AutoDisableTrigger:
        assert AutoDisableTrigger(trigger.value) is trigger


def test_auto_disable_event_status_round_trip() -> None:
    for status in AutoDisableEventStatus:
        assert AutoDisableEventStatus(status.value) is status
