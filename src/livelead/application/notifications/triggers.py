"""Notification trigger layer (US-029).

The trigger layer produces `NotificationCandidate` rows from the
existing reminder, discovery-job, and event-timing sources. The
service is the only writer of in-app rows and the only caller of the
email adapter; the trigger layer never touches those tables.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from livelead.domain.discovery.models import DiscoveryJobStatus
from livelead.domain.identity import Role
from livelead.domain.notifications import (
    NotificationCandidate,
    NotificationType,
    SourceRecordType,
    upcoming_event_window,
)
from livelead.domain.reminders.classification import classify_reminder_state
from livelead.domain.reminders.models import ReminderState

logger = logging.getLogger("livelead.notifications.triggers")


def reminder_candidates_for(
    *,
    organization_id: UUID,
    reminder_id: UUID,
    lead_display_name: str,
    owner_user_id: UUID | None,
    due_date: Any,
    today: Any = None,
) -> list[NotificationCandidate]:
    """Return candidates for a reminder that just transitioned to due or overdue."""

    state = classify_reminder_state(due_date, today=today)
    if state not in (ReminderState.DUE, ReminderState.OVERDUE):
        return []
    if owner_user_id is None:
        return []
    n_type = (
        NotificationType.REMINDER_OVERDUE
        if state == ReminderState.OVERDUE
        else NotificationType.REMINDER_DUE
    )
    return [
        NotificationCandidate(
            organization_id=organization_id,
            user_id=owner_user_id,
            notification_type=n_type,
            source_record_type=SourceRecordType.REMINDER,
            source_record_id=str(reminder_id),
            title=(
                f"Follow-up overdue: {lead_display_name}"
                if n_type == NotificationType.REMINDER_OVERDUE
                else f"Follow-up due: {lead_display_name}"
            ),
            summary=(
                f"Lead {lead_display_name} has a follow-up date of {due_date.isoformat() if hasattr(due_date, 'isoformat') else due_date}."
            ),
            deep_link=f"/leads?reminder={reminder_id}",
        )
    ]


def discovery_job_candidates_for(
    *,
    organization_id: UUID,
    job_id: UUID,
    job_status: DiscoveryJobStatus,
    creator_user_id: UUID | None,
    campaign_name: str = "",
) -> list[NotificationCandidate]:
    """Return candidates for a discovery-job state transition."""

    mapping: dict[DiscoveryJobStatus, NotificationType] = {
        DiscoveryJobStatus.SUCCEEDED: NotificationType.JOB_COMPLETED,
        DiscoveryJobStatus.FAILED: NotificationType.JOB_FAILED,
        DiscoveryJobStatus.NEEDS_USER_ACTION: NotificationType.JOB_NEEDS_USER_ACTION,
        DiscoveryJobStatus.PARTIAL: NotificationType.JOB_NEEDS_USER_ACTION,
    }
    n_type = mapping.get(job_status)
    if n_type is None or creator_user_id is None:
        return []
    title_prefix = {
        NotificationType.JOB_COMPLETED: "Discovery job complete",
        NotificationType.JOB_FAILED: "Discovery job failed",
        NotificationType.JOB_NEEDS_USER_ACTION: "Discovery job needs action",
    }[n_type]
    suffix = f" for {campaign_name}" if campaign_name else ""
    return [
        NotificationCandidate(
            organization_id=organization_id,
            user_id=creator_user_id,
            notification_type=n_type,
            source_record_type=SourceRecordType.DISCOVERY_JOB,
            source_record_id=str(job_id),
            title=f"{title_prefix}{suffix}",
            summary=(
                f"Discovery job {job_id} is now {job_status.value}."
            ),
            deep_link=f"/campaigns?job={job_id}",
        )
    ]


def upcoming_event_candidates_for(
    *,
    organization_id: UUID,
    event_id: UUID,
    event_title: str,
    starts_at: datetime | None,
    recipients: list[tuple[UUID, Role]],
    now: datetime | None = None,
    lead_minutes: int = 60,
) -> list[NotificationCandidate]:
    """Return candidates for an event whose start time is within the lead window."""

    if not upcoming_event_window(starts_at, now=now, lead_minutes=lead_minutes):
        return []
    return [
        NotificationCandidate(
            organization_id=organization_id,
            user_id=user_id,
            notification_type=NotificationType.EVENT_UPCOMING,
            source_record_type=SourceRecordType.EVENT,
            source_record_id=str(event_id),
            title=f"Upcoming: {event_title}",
            summary=(
                f"Event {event_title} starts at "
                f"{starts_at.isoformat() if starts_at else 'soon'}."
            ),
            deep_link=f"/events/{event_id}",
        )
        for user_id, _role in recipients
    ]


__all__ = [
    "discovery_job_candidates_for",
    "reminder_candidates_for",
    "upcoming_event_candidates_for",
]
