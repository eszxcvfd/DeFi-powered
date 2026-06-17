"""Tests for the webhook enums (US-049)."""

from __future__ import annotations

from livelead.domain.webhooks.enums import (
    WebhookDeliveryStatus,
    WebhookEventType,
)


def test_webhook_event_type_is_closed() -> None:
    assert set(WebhookEventType) == {
        WebhookEventType.EVENT_HIGH_PRIORITY,
        WebhookEventType.LEAD_STAGE_CHANGED,
        WebhookEventType.LEAD_OUTCOME_CHANGED,
        WebhookEventType.DISCOVERY_JOB_FAILED,
        WebhookEventType.CONNECTOR_AUTO_DISABLE_TRIGGERED,
        WebhookEventType.CONNECTOR_AUTO_DISABLE_RECOVERED,
        WebhookEventType.ALERT_FIRED,
    }


def test_webhook_event_type_values_are_stable_strings() -> None:
    assert (
        WebhookEventType.EVENT_HIGH_PRIORITY.value
        == "event.high_priority"
    )
    assert (
        WebhookEventType.LEAD_STAGE_CHANGED.value
        == "lead.stage_changed"
    )
    assert (
        WebhookEventType.LEAD_OUTCOME_CHANGED.value
        == "lead.outcome_changed"
    )
    assert (
        WebhookEventType.DISCOVERY_JOB_FAILED.value
        == "discovery.job_failed"
    )
    assert (
        WebhookEventType.CONNECTOR_AUTO_DISABLE_TRIGGERED.value
        == "connector.auto_disable_triggered"
    )
    assert (
        WebhookEventType.CONNECTOR_AUTO_DISABLE_RECOVERED.value
        == "connector.auto_disable_recovered"
    )
    assert WebhookEventType.ALERT_FIRED.value == "alert.fired"


def test_webhook_delivery_status_is_closed() -> None:
    assert set(WebhookDeliveryStatus) == {
        WebhookDeliveryStatus.PENDING,
        WebhookDeliveryStatus.IN_FLIGHT,
        WebhookDeliveryStatus.SUCCEEDED,
        WebhookDeliveryStatus.FAILED,
        WebhookDeliveryStatus.DEAD_LETTER,
        WebhookDeliveryStatus.CANCELLED,
    }


def test_webhook_delivery_status_values_are_stable_strings() -> None:
    assert WebhookDeliveryStatus.PENDING.value == "pending"
    assert WebhookDeliveryStatus.IN_FLIGHT.value == "in_flight"
    assert WebhookDeliveryStatus.SUCCEEDED.value == "succeeded"
    assert WebhookDeliveryStatus.FAILED.value == "failed"
    assert WebhookDeliveryStatus.DEAD_LETTER.value == "dead_letter"
    assert WebhookDeliveryStatus.CANCELLED.value == "cancelled"


def test_webhook_event_type_round_trip() -> None:
    for event in WebhookEventType:
        assert WebhookEventType(event.value) is event


def test_webhook_delivery_status_round_trip() -> None:
    for status in WebhookDeliveryStatus:
        assert WebhookDeliveryStatus(status.value) is status
