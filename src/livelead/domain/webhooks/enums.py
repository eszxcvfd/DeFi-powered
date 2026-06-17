"""Webhook delivery domain enums (US-049).

Closed enumerations that the bounded
`WebhookDeliveryService`, the
`WebhookSigner`, the `WebhookRetryPolicy`,
the `WebhookDispatcher`, the audit entry
shape, the `US-026` audit log, the
`US-041` alert channel, the `US-048`
auto-disable channel, and the
`US-003` secret manager share. The values
are persisted as strings so the migration
can use stable SQL `VARCHAR` columns; the
application layer normalises back to these
enums at the boundary.

The vocabulary follows
`docs/decisions/0027-webhook-delivery-and-fanout-baseline.md`
and `SPEC.md` section 7.4 Webhook
contract.
"""

from __future__ import annotations

from enum import StrEnum


class WebhookEventType(StrEnum):
    """Closed set of webhook event types the
    bounded `WebhookDeliveryService` emits.

    The bounded service reads the event type
    from the closed `AuditAction` enum from
    `US-026` and the closed
    `AutoDisableTrigger` enum from `US-048`.
    New event types cannot be added without
    first extending the
    `WebhookDeliveryService` and the audit
    entry shape.
    """

    EVENT_HIGH_PRIORITY = "event.high_priority"
    LEAD_STAGE_CHANGED = "lead.stage_changed"
    LEAD_OUTCOME_CHANGED = "lead.outcome_changed"
    DISCOVERY_JOB_FAILED = "discovery.job_failed"
    CONNECTOR_AUTO_DISABLE_TRIGGERED = (
        "connector.auto_disable_triggered"
    )
    CONNECTOR_AUTO_DISABLE_RECOVERED = (
        "connector.auto_disable_recovered"
    )
    ALERT_FIRED = "alert.fired"


class WebhookDeliveryStatus(StrEnum):
    """Closed set of webhook delivery status
    values.

    The bounded service uses the status to
    track the lifecycle of a webhook
    delivery.
    """

    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"


__all__ = [
    "WebhookDeliveryStatus",
    "WebhookEventType",
]
