from livelead.domain.browser.navigation import (
    NavigationOutcome,
    classify_http_status,
)


def test_http_403_needs_user_action():
    r = classify_http_status(403, url="https://economist.com/article")
    assert r.outcome == NavigationOutcome.NEEDS_USER_ACTION
    assert "403" in r.user_message
    assert "blocked" in r.user_message.lower() or "login" in r.user_message.lower()


def test_http_200_ok():
    r = classify_http_status(200, url="https://example.com")
    assert r.outcome == NavigationOutcome.OK
