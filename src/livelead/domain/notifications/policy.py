"""Notification pure rules (US-029)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from livelead.domain.notifications.models import (
    DEFAULT_EMAIL_PREFERENCES,
    DEFAULT_IN_APP_PREFERENCES,
    NotificationCandidate,
    NotificationChannel,
    NotificationPreference,
    NotificationState,
    NotificationType,
)


def is_email_eligible(notification_type: NotificationType) -> bool:
    """Email channel eligibility for a given notification type.

    The first slice ships email for `event_upcoming`, `job_failed`,
    `job_needs_user_action`, and `reminder_overdue`. The other types
    stay in-app only so the operator-facing signal does not turn into
    bulk outreach.
    """

    return notification_type in {
        NotificationType.JOB_FAILED,
        NotificationType.JOB_NEEDS_USER_ACTION,
        NotificationType.REMINDER_OVERDUE,
        NotificationType.EVENT_UPCOMING,
    }


def should_create_in_app(
    notification_type: NotificationType,
    preferences: list[NotificationPreference] | None,
) -> bool:
    """Decide whether a candidate should create an in-app row."""

    if preferences is None:
        return DEFAULT_IN_APP_PREFERENCES.get(notification_type, True)
    for pref in preferences:
        if pref.notification_type == notification_type:
            return pref.in_app_enabled
    return DEFAULT_IN_APP_PREFERENCES.get(notification_type, True)


def should_attempt_email(
    notification_type: NotificationType,
    preferences: list[NotificationPreference] | None,
) -> bool:
    """Decide whether a candidate should attempt an email delivery."""

    if not is_email_eligible(notification_type):
        return False
    if preferences is None:
        return DEFAULT_EMAIL_PREFERENCES.get(notification_type, False)
    for pref in preferences:
        if pref.notification_type == notification_type:
            return pref.email_enabled
    return DEFAULT_EMAIL_PREFERENCES.get(notification_type, False)


def derive_inbox_state(notification_type: NotificationType) -> NotificationState:
    return NotificationState.UNREAD


def upcoming_event_window(
    event_starts_at: datetime | None,
    *,
    now: datetime | None = None,
    lead_minutes: int = 60,
) -> bool:
    """Decide whether the event is within the bounded lead window.

    The first slice flags events that start within ``lead_minutes``
    from ``now`` and have not started yet. Events with no trustworthy
    start time are never flagged.
    """

    if event_starts_at is None:
        return False
    ref = now or datetime.now(UTC)
    if event_starts_at <= ref:
        return False
    return event_starts_at - ref <= timedelta(minutes=lead_minutes)


def summarize_candidate(candidate: NotificationCandidate) -> tuple[str, str, str]:
    """Produce (subject, body, deep_link) tuples for the email adapter.

    Returns a tuple of stable, redacted strings that the email
    adapter can send without exposing the candidate object
    directly.
    """

    subject = f"[LiveLead] {candidate.title}"
    body = (
        f"{candidate.summary}\n\n"
        f"Open in LiveLead: {candidate.deep_link}\n"
        f"(reference: {candidate.source_record_type.value}/{candidate.source_record_id})"
    )
    return subject, body, candidate.deep_link


def normalize_preference_payload(
    payload: dict[str, dict[str, bool]] | None,
) -> dict[NotificationType, dict[NotificationChannel, bool]]:
    """Validate a preference update payload and return a typed map.

    Unknown notification types are rejected. Unknown channel keys
    are rejected. Channel values must be booleans.
    """

    if not payload:
        return {}
    out: dict[NotificationType, dict[NotificationChannel, bool]] = {}
    for type_key, channel_map in payload.items():
        try:
            n_type = NotificationType(type_key)
        except ValueError as exc:
            raise ValueError(f"unknown notification type: {type_key}") from exc
        if not isinstance(channel_map, dict):
            raise ValueError(f"channel map for {type_key} must be an object")
        typed_channels: dict[NotificationChannel, bool] = {}
        for channel_key, value in channel_map.items():
            try:
                channel = NotificationChannel(channel_key)
            except ValueError as exc:
                raise ValueError(f"unknown channel: {channel_key}") from exc
            if not isinstance(value, bool):
                raise ValueError(
                    f"channel value for {type_key}/{channel_key} must be a boolean"
                )
            typed_channels[channel] = value
        out[n_type] = typed_channels
    return out


def default_preference_matrix() -> list[dict[str, Any]]:
    """Return the default preference matrix used to seed new users."""

    return [
        {
            "notification_type": n.value,
            "in_app_enabled": DEFAULT_IN_APP_PREFERENCES[n],
            "email_enabled": DEFAULT_EMAIL_PREFERENCES.get(n, False),
        }
        for n in NotificationType
    ]


__all__ = [
    "default_preference_matrix",
    "derive_inbox_state",
    "is_email_eligible",
    "normalize_preference_payload",
    "should_attempt_email",
    "should_create_in_app",
    "summarize_candidate",
    "upcoming_event_window",
]
