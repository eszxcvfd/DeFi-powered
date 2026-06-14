from livelead.domain.leads.event_defaults import lead_identity_from_event


def test_identity_uses_event_title_not_organizer_only():
    out = lead_identity_from_event(
        canonical_title="B2B Payments Webinar — techcrunch-com #1",
        organizer="Org techcrunch-com",
        region="EU",
        source_url="https://techcrunch.com/events/x",
    )
    assert out["display_name"].startswith("B2B Payments")
    assert out["company"] == "Org techcrunch-com"
    assert "EU" in out["title"]
    assert "Event:" in out["notes"]


def test_two_events_same_organizer_different_titles():
    a = lead_identity_from_event(
        canonical_title="Fintech Summit — techcrunch-com #2",
        organizer="Org techcrunch-com",
        region="US",
    )
    b = lead_identity_from_event(
        canonical_title="Developer Workshop — techcrunch-com #3",
        organizer="Org techcrunch-com",
        region="Global",
    )
    assert a["display_name"] != b["display_name"]
    assert a["company"] == b["company"] == "Org techcrunch-com"
