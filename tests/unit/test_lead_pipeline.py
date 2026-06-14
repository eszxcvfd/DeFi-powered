from uuid import uuid4

from livelead.domain.leads.models import LeadOriginKind, LeadRecord, LeadStage
from livelead.domain.leads.validation import (
    find_duplicate,
    may_transition_stage,
    normalize_public_url,
    rejects_sensitive_inference,
    validate_origin,
)


def test_validate_origin_event_requires_event_id():
    assert (
        validate_origin(
            origin_kind=LeadOriginKind.EVENT,
            event_id=None,
            manual_entry_note="",
            discovery_source="event",
        )
        is not None
    )


def test_validate_origin_manual_requires_note():
    assert (
        validate_origin(
            origin_kind=LeadOriginKind.MANUAL,
            event_id=None,
            manual_entry_note="",
            discovery_source="",
        )
        is not None
    )


def test_duplicate_public_url():
    existing = [
        LeadRecord(
            id=uuid4(),
            organization_id=uuid4(),
            campaign_id=None,
            display_name="A",
            company="Co",
            title="",
            public_url="https://Example.com/path",
            discovery_source="event",
            event_id=None,
            interests="",
            pain_points="",
            owner="",
            stage=LeadStage.NEWLY_DISCOVERED,
            lawful_basis_note="",
            follow_up_date=None,
            notes="",
            manual_entry_note="",
            origin_kind=LeadOriginKind.EVENT,
            email_hash="",
            external_id="",
            created_by="a",
            created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            updated_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        )
    ]
    dup = find_duplicate({"public_url": "http://example.com/path"}, existing)
    assert dup is not None
    assert dup.reason == "duplicate public_url"


def test_sensitive_inference_rejected():
    assert rejects_sensitive_inference("inferred sensitive trait from scrape")


def test_stage_transition_from_not_fit_blocked():
    assert not may_transition_stage(LeadStage.NOT_FIT, LeadStage.WATCHED)


def test_normalize_url():
    assert normalize_public_url("HTTPS://Foo.COM/bar/") == "foo.com/bar"


def test_event_linked_allows_same_organizer_different_events():
    org = uuid4()
    event_a, event_b = uuid4(), uuid4()
    existing = [
        LeadRecord(
            id=uuid4(),
            organization_id=org,
            campaign_id=None,
            display_name="Acme Org",
            company="Acme Org",
            title="",
            public_url="https://x.test/a",
            discovery_source="event",
            event_id=event_a,
            interests="",
            pain_points="",
            owner="",
            stage=LeadStage.NEWLY_DISCOVERED,
            lawful_basis_note="",
            follow_up_date=None,
            notes="",
            manual_entry_note="",
            origin_kind=LeadOriginKind.EVENT,
            email_hash="",
            external_id="",
            created_by="a",
            created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            updated_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        )
    ]
    dup = find_duplicate(
        {
            "display_name": "Acme Org",
            "company": "Acme Org",
            "public_url": "https://x.test/b#other",
            "event_id": str(event_b),
        },
        existing,
    )
    assert dup is None


def test_duplicate_event_link():
    org = uuid4()
    eid = uuid4()
    lid = uuid4()
    existing = [
        LeadRecord(
            id=lid,
            organization_id=org,
            campaign_id=None,
            display_name="X",
            company="",
            title="",
            public_url="",
            discovery_source="event",
            event_id=eid,
            interests="",
            pain_points="",
            owner="",
            stage=LeadStage.NEWLY_DISCOVERED,
            lawful_basis_note="",
            follow_up_date=None,
            notes="",
            manual_entry_note="",
            origin_kind=LeadOriginKind.EVENT,
            email_hash="",
            external_id="",
            created_by="a",
            created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            updated_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        )
    ]
    dup = find_duplicate({"event_id": str(eid), "display_name": "Y", "company": ""}, existing)
    assert dup is not None
    assert dup.reason == "duplicate event link"
