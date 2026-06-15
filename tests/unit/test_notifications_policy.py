"""Notification domain rules (US-029)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from livelead.domain.discovery.models import DiscoveryJobStatus
from livelead.domain.identity import Role
from livelead.domain.notifications import (
    DEFAULT_EMAIL_PREFERENCES,
    DEFAULT_IN_APP_PREFERENCES,
    NotificationCandidate,
    NotificationChannel,
    NotificationPreference,
    NotificationType,
    SourceRecordType,
    default_preference_matrix,
    is_email_eligible,
    normalize_preference_payload,
    should_attempt_email,
    should_create_in_app,
    summarize_candidate,
    upcoming_event_window,
)
from livelead.domain.notifications.models import DeliveryStatus, NotificationState
from livelead.application.notifications import (
    discovery_job_candidates_for,
    reminder_candidates_for,
    upcoming_event_candidates_for,
)


# --- helpers ----------------------------------------------------------
def _pref(n_type: NotificationType, *, in_app: bool = True, email: bool = False) -> NotificationPreference:
    return NotificationPreference(
        id=uuid4(),
        organization_id=uuid4(),
        user_id=uuid4(),
        notification_type=n_type,
        in_app_enabled=in_app,
        email_enabled=email,
        updated_at=datetime.now(UTC),
    )


# --- eligibility + preference defaults --------------------------------
def test_email_eligibility_matches_design():
    assert is_email_eligible(NotificationType.JOB_FAILED) is True
    assert is_email_eligible(NotificationType.JOB_NEEDS_USER_ACTION) is True
    assert is_email_eligible(NotificationType.REMINDER_OVERDUE) is True
    assert is_email_eligible(NotificationType.EVENT_UPCOMING) is True
    assert is_email_eligible(NotificationType.REMINDER_DUE) is False
    assert is_email_eligible(NotificationType.JOB_COMPLETED) is False


def test_default_email_preferences_match_design():
    assert DEFAULT_EMAIL_PREFERENCES[NotificationType.JOB_FAILED] is True
    assert DEFAULT_EMAIL_PREFERENCES[NotificationType.REMINDER_DUE] is False
    assert DEFAULT_EMAIL_PREFERENCES[NotificationType.REMINDER_OVERDUE] is True


def test_should_create_in_app_falls_back_to_default_when_no_preference():
    assert should_create_in_app(NotificationType.JOB_COMPLETED, None) is True


def test_should_create_in_app_honors_user_preference():
    prefs = [_pref(NotificationType.JOB_COMPLETED, in_app=False)]
    assert should_create_in_app(NotificationType.JOB_COMPLETED, prefs) is False


def test_should_attempt_email_requires_eligibility():
    # Ineligible type never attempts email.
    assert should_attempt_email(NotificationType.REMINDER_DUE, None) is False
    assert should_attempt_email(NotificationType.JOB_COMPLETED, None) is False
    # Eligible but disabled by default + no preference row stays default.
    assert should_attempt_email(NotificationType.EVENT_UPCOMING, None) is True


def test_should_attempt_email_honors_user_preference():
    prefs = [_pref(NotificationType.EVENT_UPCOMING, email=False)]
    assert should_attempt_email(NotificationType.EVENT_UPCOMING, prefs) is False
    prefs2 = [_pref(NotificationType.EVENT_UPCOMING, email=True)]
    assert should_attempt_email(NotificationType.EVENT_UPCOMING, prefs2) is True


# --- payload normalization --------------------------------------------
def test_normalize_preference_payload_accepts_typed_input():
    payload = {
        "event_upcoming": {"in_app": True, "email": False},
        "reminder_due": {"in_app": True},
    }
    typed = normalize_preference_payload(payload)
    assert typed[NotificationType.EVENT_UPCOMING][NotificationChannel.IN_APP] is True
    assert typed[NotificationType.EVENT_UPCOMING][NotificationChannel.EMAIL] is False
    assert typed[NotificationType.REMINDER_DUE][NotificationChannel.IN_APP] is True


def test_normalize_preference_payload_rejects_unknown_type():
    with pytest.raises(ValueError):
        normalize_preference_payload({"unknown_type": {"in_app": True}})


def test_normalize_preference_payload_rejects_unknown_channel():
    with pytest.raises(ValueError):
        normalize_preference_payload(
            {"event_upcoming": {"carrier_pigeon": True}}
        )


def test_normalize_preference_payload_rejects_non_boolean_value():
    with pytest.raises(ValueError):
        normalize_preference_payload(
            {"event_upcoming": {"in_app": "yes"}}
        )


def test_normalize_preference_payload_handles_empty():
    assert normalize_preference_payload(None) == {}
    assert normalize_preference_payload({}) == {}


# --- default matrix shape --------------------------------------------
def test_default_preference_matrix_covers_every_type():
    matrix = default_preference_matrix()
    types = {row["notification_type"] for row in matrix}
    expected = {n.value for n in NotificationType}
    assert types == expected


# --- upcoming event window --------------------------------------------
def test_upcoming_event_window_returns_false_for_missing_start():
    assert upcoming_event_window(None) is False


def test_upcoming_event_window_returns_false_for_past_event():
    now = datetime.now(UTC)
    assert upcoming_event_window(now - timedelta(minutes=10), now=now) is False


def test_upcoming_event_window_returns_true_within_lead_minutes():
    now = datetime.now(UTC)
    starts_at = now + timedelta(minutes=30)
    assert upcoming_event_window(starts_at, now=now, lead_minutes=60) is True


def test_upcoming_event_window_returns_false_outside_lead_minutes():
    now = datetime.now(UTC)
    starts_at = now + timedelta(hours=5)
    assert upcoming_event_window(starts_at, now=now, lead_minutes=60) is False


# --- candidate builders -----------------------------------------------
def test_reminder_candidate_for_due_state():
    org = uuid4()
    user = uuid4()
    reminder_id = uuid4()
    cands = reminder_candidates_for(
        organization_id=org,
        reminder_id=reminder_id,
        lead_display_name="Acme",
        owner_user_id=user,
        due_date=datetime.now(UTC).date(),
    )
    assert len(cands) == 1
    cand = cands[0]
    assert cand.notification_type == NotificationType.REMINDER_DUE
    assert cand.source_record_type == SourceRecordType.REMINDER
    assert cand.source_record_id == str(reminder_id)


def test_reminder_candidate_for_overdue_state_uses_overdue_type():
    org = uuid4()
    user = uuid4()
    cands = reminder_candidates_for(
        organization_id=org,
        reminder_id=uuid4(),
        lead_display_name="Acme",
        owner_user_id=user,
        due_date=datetime.now(UTC).date() - timedelta(days=3),
    )
    assert len(cands) == 1
    assert cands[0].notification_type == NotificationType.REMINDER_OVERDUE


def test_reminder_candidate_skips_when_owner_unknown():
    cands = reminder_candidates_for(
        organization_id=uuid4(),
        reminder_id=uuid4(),
        lead_display_name="Acme",
        owner_user_id=None,
        due_date=datetime.now(UTC).date(),
    )
    assert cands == []


def test_reminder_candidate_skips_when_due_date_in_future():
    cands = reminder_candidates_for(
        organization_id=uuid4(),
        reminder_id=uuid4(),
        lead_display_name="Acme",
        owner_user_id=uuid4(),
        due_date=datetime.now(UTC).date() + timedelta(days=3),
    )
    assert cands == []


def test_discovery_job_candidate_for_succeeded_state():
    cands = discovery_job_candidates_for(
        organization_id=uuid4(),
        job_id=uuid4(),
        job_status=DiscoveryJobStatus.SUCCEEDED,
        creator_user_id=uuid4(),
        campaign_name="Acme Discovery",
    )
    assert len(cands) == 1
    cand = cands[0]
    assert cand.notification_type == NotificationType.JOB_COMPLETED
    assert cand.source_record_type == SourceRecordType.DISCOVERY_JOB
    assert "Acme Discovery" in cand.title


def test_discovery_job_candidate_for_failed_and_needs_user_action():
    failed = discovery_job_candidates_for(
        organization_id=uuid4(),
        job_id=uuid4(),
        job_status=DiscoveryJobStatus.FAILED,
        creator_user_id=uuid4(),
    )
    assert failed[0].notification_type == NotificationType.JOB_FAILED
    needs = discovery_job_candidates_for(
        organization_id=uuid4(),
        job_id=uuid4(),
        job_status=DiscoveryJobStatus.NEEDS_USER_ACTION,
        creator_user_id=uuid4(),
    )
    assert needs[0].notification_type == NotificationType.JOB_NEEDS_USER_ACTION


def test_discovery_job_candidate_skips_unknown_state():
    cands = discovery_job_candidates_for(
        organization_id=uuid4(),
        job_id=uuid4(),
        job_status=DiscoveryJobStatus.QUEUED,
        creator_user_id=uuid4(),
    )
    assert cands == []


def test_discovery_job_candidate_skips_when_creator_unknown():
    cands = discovery_job_candidates_for(
        organization_id=uuid4(),
        job_id=uuid4(),
        job_status=DiscoveryJobStatus.SUCCEEDED,
        creator_user_id=None,
    )
    assert cands == []


def test_upcoming_event_candidates_target_active_memberships():
    org = uuid4()
    event_id = uuid4()
    starts_at = datetime.now(UTC) + timedelta(minutes=15)
    user_a = uuid4()
    user_b = uuid4()
    cands = upcoming_event_candidates_for(
        organization_id=org,
        event_id=event_id,
        event_title="Acme Event",
        starts_at=starts_at,
        recipients=[(user_a, Role.OWNER), (user_b, Role.ANALYST)],
        lead_minutes=60,
    )
    assert len(cands) == 2
    assert {c.user_id for c in cands} == {user_a, user_b}
    assert all(c.notification_type == NotificationType.EVENT_UPCOMING for c in cands)


def test_upcoming_event_candidates_skip_when_outside_window():
    cands = upcoming_event_candidates_for(
        organization_id=uuid4(),
        event_id=uuid4(),
        event_title="Acme Event",
        starts_at=datetime.now(UTC) + timedelta(hours=12),
        recipients=[(uuid4(), Role.OWNER)],
        lead_minutes=60,
    )
    assert cands == []


# --- candidate summarization -----------------------------------------
def test_summarize_candidate_produces_safe_strings():
    cand = NotificationCandidate(
        organization_id=uuid4(),
        user_id=uuid4(),
        notification_type=NotificationType.JOB_FAILED,
        source_record_type=SourceRecordType.DISCOVERY_JOB,
        source_record_id="job-1",
        title="Discovery job failed",
        summary="Campaign Acme could not complete discovery.",
        deep_link="/campaigns?job=job-1",
    )
    subject, body, link = summarize_candidate(cand)
    assert subject.startswith("[LiveLead]")
    assert "Discovery job failed" in subject
    assert "Campaign Acme could not complete discovery" in body
    assert link == "/campaigns?job=job-1"
    assert "discovery_job/job-1" in body


# --- state enums round-trip through the model ------------------------
def test_notification_state_values_are_stable():
    assert NotificationState.UNREAD.value == "unread"
    assert NotificationState.READ.value == "read"
    assert NotificationState.DISMISSED.value == "dismissed"
    assert DeliveryStatus.SUCCEEDED.value == "succeeded"
    assert DeliveryStatus.FAILED.value == "failed"
    assert DeliveryStatus.SUPPRESSED.value == "suppressed"
