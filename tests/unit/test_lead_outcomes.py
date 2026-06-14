from datetime import UTC, datetime
from uuid import uuid4

from livelead.domain.leads.models import (
    LeadActivityEntry,
    LeadActivityKind,
    LeadOriginKind,
    LeadRecord,
    LeadStage,
)
from livelead.domain.leads.outcomes import (
    OutcomeType,
    derive_latest_outcome,
    may_record_outcome,
    parse_outcome_type,
)


def _lead(stage: LeadStage) -> LeadRecord:
    now = datetime.now(UTC)
    return LeadRecord(
        id=uuid4(),
        organization_id=uuid4(),
        campaign_id=None,
        display_name="A",
        company="",
        title="",
        public_url="",
        discovery_source="event",
        event_id=uuid4(),
        interests="",
        pain_points="",
        owner="",
        stage=stage,
        lawful_basis_note="",
        follow_up_date=None,
        notes="",
        manual_entry_note="",
        origin_kind=LeadOriginKind.EVENT,
        email_hash="",
        external_id="",
        created_by="analyst",
        created_at=now,
        updated_at=now,
    )


def test_parse_outcome_type():
    assert parse_outcome_type("contact") == OutcomeType.CONTACT
    assert parse_outcome_type("MEETING") == OutcomeType.MEETING
    assert parse_outcome_type("bad") is None


def test_may_record_opportunity_on_newly_discovered_blocked():
    assert (
        may_record_outcome(_lead(LeadStage.NEWLY_DISCOVERED), OutcomeType.OPPORTUNITY) is not None
    )


def test_may_record_contact_on_newly_discovered_ok():
    assert may_record_outcome(_lead(LeadStage.NEWLY_DISCOVERED), OutcomeType.CONTACT) is None


def test_may_record_response_on_newly_discovered_ok():
    assert may_record_outcome(_lead(LeadStage.NEWLY_DISCOVERED), OutcomeType.RESPONSE) is None


def test_may_record_not_fit_blocked():
    assert may_record_outcome(_lead(LeadStage.NOT_FIT), OutcomeType.CONTACT) is not None


def test_derive_latest_outcome_newest_first():
    lid = uuid4()
    now = datetime.now(UTC)
    older = LeadActivityEntry(
        id=uuid4(),
        lead_id=lid,
        kind=LeadActivityKind.OUTCOME_RECORDED,
        actor="a",
        body="old",
        from_stage="",
        to_stage="",
        created_at=now,
        outcome_type="contact",
        occurred_at=now,
    )
    newer = LeadActivityEntry(
        id=uuid4(),
        lead_id=lid,
        kind=LeadActivityKind.OUTCOME_RECORDED,
        actor="b",
        body="new",
        from_stage="",
        to_stage="",
        created_at=now,
        outcome_type="meeting",
        occurred_at=now,
    )
    latest = derive_latest_outcome([newer, older])
    assert latest and latest.outcome_type == OutcomeType.MEETING
