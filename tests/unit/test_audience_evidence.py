from livelead.domain.audience.evidence import (
    icp_industry_in_event_text,
    is_likely_fixture_event_title,
    text_has_partner_signal,
)


def test_fixture_title_detected():
    assert is_likely_fixture_event_title("Developer API Workshop — hnrss-org-1")


def test_partner_requires_event_wording():
    assert not text_has_partner_signal("Software, AI, Developer Tools launch event")
    assert text_has_partner_signal("Stripe partnership summit for APIs")


def test_icp_not_in_event_text():
    assert not icp_industry_in_event_text("Payments", "crypto hackathon SF")
