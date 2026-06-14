from livelead.domain.content.risk import evaluate_draft_risks


def test_promotional_flag():
    flags = evaluate_draft_risks(
        "Act now guaranteed results", event_title="Payments Webinar EU", cta="Buy"
    )
    codes = {f.code.value for f in flags}
    assert "overly_promotional" in codes


def test_sensitive_flag():
    flags = evaluate_draft_risks("Targeting political voters only", event_title="Event X", cta="Hi")
    assert any(f.code.value == "sensitive_targeting" for f in flags)
