"""Row mappers for the webhook delivery tables (US-049)."""

from __future__ import annotations

import json
from typing import Any

from livelead.domain.webhooks.enums import (
    WebhookDeliveryStatus,
    WebhookEventType,
)
from livelead.domain.webhooks.models import (
    WebhookDelivery,
    WebhookSigningSecret,
    WebhookSubscription,
)
from livelead.infrastructure.db.models import (
    WebhookDeliveryRow,
    WebhookSigningSecretRow,
    WebhookSubscriptionRow,
)


def _event_type_from_string(value: str | None) -> WebhookEventType:
    if not value:
        return WebhookEventType.ALERT_FIRED
    try:
        return WebhookEventType(value)
    except ValueError:
        return WebhookEventType.ALERT_FIRED


def _delivery_status_from_string(
    value: str | None,
) -> WebhookDeliveryStatus:
    if not value:
        return WebhookDeliveryStatus.PENDING
    try:
        return WebhookDeliveryStatus(value)
    except ValueError:
        return WebhookDeliveryStatus.PENDING


def _event_types_from_json(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return ()
    if not isinstance(data, list):
        return ()
    return tuple(str(x) for x in data if isinstance(x, str))


def row_to_webhook_subscription(
    row: WebhookSubscriptionRow,
) -> WebhookSubscription:
    return WebhookSubscription(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name or "",
        target_url=row.target_url or "",
        secret_id=row.secret_id or "",
        event_types=_event_types_from_json(row.event_types_json),
        enabled=bool(row.enabled),
        created_by=row.created_by or "system",
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_rotated_at=row.last_rotated_at,
        last_success_at=row.last_success_at,
        last_failure_at=row.last_failure_at,
        deleted_at=row.deleted_at,
    )


def row_to_webhook_signing_secret(
    row: WebhookSigningSecretRow,
) -> WebhookSigningSecret:
    return WebhookSigningSecret(
        id=row.id,
        organization_id=row.organization_id,
        subscription_id=row.subscription_id,
        secret_ciphertext=row.secret_ciphertext or "",
        version=int(row.version or 1),
        created_at=row.created_at,
        rotated_at=row.rotated_at,
    )


def row_to_webhook_delivery(
    row: WebhookDeliveryRow,
) -> WebhookDelivery:
    return WebhookDelivery(
        id=row.id,
        organization_id=row.organization_id,
        subscription_id=row.subscription_id,
        event_id=row.event_id,
        event_type=_event_type_from_string(row.event_type),
        target_url=row.target_url or "",
        payload_hash=row.payload_hash or "",
        request_body=row.request_body or "",
        signature=row.signature or "",
        status=_delivery_status_from_string(row.status),
        attempt_count=int(row.attempt_count or 0),
        next_attempt_at=row.next_attempt_at,
        last_attempt_at=row.last_attempt_at,
        last_response_code=row.last_response_code,
        last_response_message=row.last_response_message,
        delivered_at=row.delivered_at,
        created_at=row.created_at,
    )


__all__ = [
    "row_to_webhook_delivery",
    "row_to_webhook_signing_secret",
    "row_to_webhook_subscription",
]
