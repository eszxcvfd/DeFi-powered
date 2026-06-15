"""ORM -> domain mapping for notifications (US-029)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from livelead.domain.notifications import (
    DeliveryStatus,
    NotificationChannel,
    NotificationDeliveryAttempt,
    NotificationPreference,
    NotificationState,
    NotificationType,
    SourceRecordType,
    UserNotification,
)
from livelead.infrastructure.db.models import (
    NotificationDeliveryAttemptRow,
    NotificationPreferenceRow,
    UserNotificationRow,
)


def _uuid(value: str | UUID | None) -> UUID | None:
    if value is None:
        return None
    return value if isinstance(value, UUID) else UUID(str(value))


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def row_to_user_notification(row: UserNotificationRow) -> UserNotification:
    return UserNotification(
        id=_uuid(row.id) or UUID(str(row.id)),
        organization_id=_uuid(row.organization_id) or UUID(str(row.organization_id)),
        user_id=_uuid(row.user_id) or UUID(str(row.user_id)),
        notification_type=NotificationType(str(row.notification_type)),
        state=NotificationState(str(row.state)),
        source_record_type=SourceRecordType(str(row.source_record_type)),
        source_record_id=str(row.source_record_id),
        title=str(row.title),
        summary=str(row.summary or ""),
        deep_link=str(row.deep_link or ""),
        created_at=_ensure_utc(row.created_at) or datetime.now(UTC),
        read_at=_ensure_utc(row.read_at),
        dismissed_at=_ensure_utc(row.dismissed_at),
    )


def row_to_notification_preference(row: NotificationPreferenceRow) -> NotificationPreference:
    return NotificationPreference(
        id=_uuid(row.id) or UUID(str(row.id)),
        organization_id=_uuid(row.organization_id) or UUID(str(row.organization_id)),
        user_id=_uuid(row.user_id) or UUID(str(row.user_id)),
        notification_type=NotificationType(str(row.notification_type)),
        in_app_enabled=bool(row.in_app_enabled),
        email_enabled=bool(row.email_enabled),
        updated_at=_ensure_utc(row.updated_at) or datetime.now(UTC),
    )


def row_to_delivery_attempt(row: NotificationDeliveryAttemptRow) -> NotificationDeliveryAttempt:
    try:
        diagnostics = json.loads(row.diagnostics_json or "{}")
    except (TypeError, ValueError):
        diagnostics = {}
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    return NotificationDeliveryAttempt(
        id=_uuid(row.id) or UUID(str(row.id)),
        organization_id=_uuid(row.organization_id) or UUID(str(row.organization_id)),
        user_id=_uuid(row.user_id) or UUID(str(row.user_id)),
        notification_id=_uuid(row.notification_id) or UUID(str(row.notification_id)),
        notification_type=NotificationType(str(row.notification_type)),
        channel=NotificationChannel(str(row.channel)),
        status=DeliveryStatus(str(row.status)),
        provider=str(row.provider),
        provider_message_id=str(row.provider_message_id or ""),
        recipient=str(row.recipient or ""),
        subject=str(row.subject or ""),
        diagnostics=diagnostics,
        attempted_at=_ensure_utc(row.attempted_at) or datetime.now(UTC),
    )


__all__ = [
    "row_to_user_notification",
    "row_to_notification_preference",
    "row_to_delivery_attempt",
]
