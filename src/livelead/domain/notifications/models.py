"""Notification domain types (US-029)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class NotificationType(StrEnum):
    JOB_COMPLETED = "job_completed"
    JOB_NEEDS_USER_ACTION = "job_needs_user_action"
    JOB_FAILED = "job_failed"
    REMINDER_DUE = "reminder_due"
    REMINDER_OVERDUE = "reminder_overdue"
    EVENT_UPCOMING = "event_upcoming"


class NotificationChannel(StrEnum):
    IN_APP = "in_app"
    EMAIL = "email"


class NotificationState(StrEnum):
    UNREAD = "unread"
    READ = "read"
    DISMISSED = "dismissed"


class SourceRecordType(StrEnum):
    DISCOVERY_JOB = "discovery_job"
    REMINDER = "reminder"
    EVENT = "event"
    SYSTEM = "system"


class DeliveryStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SUPPRESSED = "suppressed"


# Bounded set of (type, channel) combinations the first slice ships.
# Encoded as defaults so future notification types can opt in
# explicitly without changing the preference model.
DEFAULT_IN_APP_PREFERENCES: dict[NotificationType, bool] = {
    n: True for n in NotificationType
}
DEFAULT_EMAIL_PREFERENCES: dict[NotificationType, bool] = {
    NotificationType.JOB_COMPLETED: False,
    NotificationType.JOB_NEEDS_USER_ACTION: True,
    NotificationType.JOB_FAILED: True,
    NotificationType.REMINDER_DUE: False,
    NotificationType.REMINDER_OVERDUE: True,
    NotificationType.EVENT_UPCOMING: True,
}


@dataclass(frozen=True, slots=True)
class UserNotification:
    id: UUID
    organization_id: UUID
    user_id: UUID
    notification_type: NotificationType
    state: NotificationState
    source_record_type: SourceRecordType
    source_record_id: str
    title: str
    summary: str
    deep_link: str
    created_at: datetime
    read_at: datetime | None
    dismissed_at: datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "user_id": str(self.user_id),
            "notification_type": self.notification_type.value,
            "state": self.state.value,
            "source_record_type": self.source_record_type.value,
            "source_record_id": self.source_record_id,
            "title": self.title,
            "summary": self.summary,
            "deep_link": self.deep_link,
            "created_at": self.created_at.isoformat(),
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "dismissed_at": self.dismissed_at.isoformat() if self.dismissed_at else None,
        }


@dataclass(frozen=True, slots=True)
class NotificationPreference:
    id: UUID
    organization_id: UUID
    user_id: UUID
    notification_type: NotificationType
    in_app_enabled: bool
    email_enabled: bool
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "notification_type": self.notification_type.value,
            "in_app_enabled": self.in_app_enabled,
            "email_enabled": self.email_enabled,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class NotificationDeliveryAttempt:
    id: UUID
    organization_id: UUID
    user_id: UUID
    notification_id: UUID
    notification_type: NotificationType
    channel: NotificationChannel
    status: DeliveryStatus
    provider: str
    provider_message_id: str
    recipient: str
    subject: str
    diagnostics: dict[str, Any]
    attempted_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "user_id": str(self.user_id),
            "notification_id": str(self.notification_id),
            "notification_type": self.notification_type.value,
            "channel": self.channel.value,
            "status": self.status.value,
            "provider": self.provider,
            "provider_message_id": self.provider_message_id,
            "recipient": self.recipient,
            "subject": self.subject,
            "diagnostics": self.diagnostics,
            "attempted_at": self.attempted_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class NotificationCandidate:
    """Pure decision record produced by the trigger layer.

    The service converts a candidate into an in-app row and an email
    delivery attempt. Candidates never touch the database.
    """

    organization_id: UUID
    user_id: UUID
    notification_type: NotificationType
    source_record_type: SourceRecordType
    source_record_id: str
    title: str
    summary: str
    deep_link: str


def new_notification_id() -> UUID:
    return uuid4()


def new_preference_id() -> UUID:
    return uuid4()


def new_delivery_attempt_id() -> UUID:
    return uuid4()


__all__ = [
    "DEFAULT_EMAIL_PREFERENCES",
    "DEFAULT_IN_APP_PREFERENCES",
    "DeliveryStatus",
    "NotificationCandidate",
    "NotificationChannel",
    "NotificationDeliveryAttempt",
    "NotificationPreference",
    "NotificationState",
    "NotificationType",
    "SourceRecordType",
    "UserNotification",
    "new_delivery_attempt_id",
    "new_notification_id",
    "new_preference_id",
]
