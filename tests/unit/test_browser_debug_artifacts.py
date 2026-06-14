import json
from datetime import UTC, datetime, timedelta

from livelead.domain.browser.debug_artifacts import (
    BrowserArtifactStatus,
    BrowserArtifactType,
    can_access_artifact,
    can_capture_screenshot,
    can_enable_debug,
    effective_artifact_status,
    parse_browser_artifact_policy,
    retention_expires_at,
    sanitize_text_payload,
)
from livelead.domain.browser.models import BrowserSessionState


def test_sanitize_redacts_secrets():
    text = "password=supersecret and api_key=abc123"
    out, redacted = sanitize_text_payload(text)
    assert redacted
    assert "supersecret" not in out


def test_screenshot_allowed_when_running():
    d = can_capture_screenshot(
        session_state=BrowserSessionState.RUNNING,
        policy=parse_browser_artifact_policy("{}"),
    )
    assert d.allowed


def test_retention_expiry():
    exp = retention_expires_at(
        artifact_type=BrowserArtifactType.SCREENSHOT,
        policy=parse_browser_artifact_policy(json.dumps({"browser_screenshot_retention_days": 3})),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert exp.day == 4


def test_expired_artifact_access_denied():
    d = can_access_artifact(
        status=BrowserArtifactStatus.ACTIVE,
        expires_at=datetime.now(UTC) - timedelta(hours=1),
        organization_id="a",
        artifact_org_id="a",
        actor_role="admin",
    )
    assert not d.allowed


def test_debug_enable_requires_role():
    d = can_enable_debug(policy={}, actor_role="viewer")
    assert not d.allowed