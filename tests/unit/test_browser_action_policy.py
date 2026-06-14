from livelead.domain.browser.action_policy import (
    evaluate_action_policy_with_json,
    normalize_action_parameters,
    parse_browser_action_allowlist,
)
from livelead.domain.browser.actions import BrowserActionType
from livelead.domain.browser.models import BrowserSessionState


def test_allowlist_parse_default_all():
    assert BrowserActionType.SCROLL in parse_browser_action_allowlist(None)


def test_allowlist_restricted():
    raw = '{"browser_read_only_actions": ["scroll", "read_text"]}'
    allow = parse_browser_action_allowlist(raw)
    assert BrowserActionType.SCROLL in allow
    assert BrowserActionType.NAVIGATE not in allow


def test_policy_blocks_not_allowlisted():
    allow = frozenset({BrowserActionType.SCROLL})
    d = evaluate_action_policy_with_json(
        allowlist=allow,
        session_state=BrowserSessionState.RUNNING,
        action_type=BrowserActionType.NAVIGATE,
        actions_used=0,
        max_actions=10,
    )
    assert not d.allowed
    assert "action_not_allowlisted" in d.reasons


def test_normalize_navigate_requires_url():
    params, errs = normalize_action_parameters(BrowserActionType.NAVIGATE, {})
    assert errs
    params2, errs2 = normalize_action_parameters(
        BrowserActionType.NAVIGATE, {"url": "https://example.com/x"}
    )
    assert not errs2
    assert params2["url"].startswith("https://")
