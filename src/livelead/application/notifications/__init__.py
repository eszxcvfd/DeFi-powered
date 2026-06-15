"""Notifications application layer — US-029."""

from .notification_service import (
    DeliveryView,
    InboxView,
    NotificationService,
    PreferenceMatrix,
)
from .triggers import (
    discovery_job_candidates_for,
    reminder_candidates_for,
    upcoming_event_candidates_for,
)

__all__ = [
    "DeliveryView",
    "InboxView",
    "NotificationService",
    "PreferenceMatrix",
    "discovery_job_candidates_for",
    "reminder_candidates_for",
    "upcoming_event_candidates_for",
]
