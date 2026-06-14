from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from livelead.domain.browser.lifecycle import (
    can_request_stop,
    derive_isolation_key,
    derive_profile_boundary,
    is_terminal,
    next_state_after_stop_request,
    runtime_seconds,
    validate_launch_target,
)
from livelead.domain.browser.models import BrowserEngine, BrowserSessionState, LaunchContextKind
from livelead.domain.browser.policy import BrowserLaunchDenied, evaluate_browser_launch
from livelead.domain.sources.models import (
    AccessMode,
    AuthenticationMode,
    ConnectorType,
    PolicyDecision,
    SourceGovernance,
    SourcePolicy,
)


def _source(connector=ConnectorType.BROWSER, access=AccessMode.BROWSER, approved=True):
    now = datetime.now(UTC)
    return SourceGovernance(
        id=uuid4(),
        organization_id=uuid4(),
        name="Browser source",
        domain="example.com",
        connector_type=connector,
        automation_engine="playwright",
        authentication_mode=AuthenticationMode.NONE,
        enabled=True,
        approved=approved,
        approved_at=now,
        approved_by="admin",
        policy=SourcePolicy(access_mode=access, valid=True),
        has_secret=False,
        created_at=now,
        updated_at=now,
    )


def test_validate_launch_target_event_requires_event():
    errs = validate_launch_target(
        kind=LaunchContextKind.EVENT,
        event_id_present=False,
        source_id_present=True,
        initial_url="https://x.test",
    )
    assert "event_required" in errs


def test_isolation_metadata_unique_per_session():
    org = str(uuid4())
    sid = str(uuid4())
    assert derive_isolation_key(org, sid) != derive_isolation_key(org, str(uuid4()))
    assert "workspace/" in derive_profile_boundary(org, sid)


def test_stop_eligibility_and_transition():
    assert can_request_stop(BrowserSessionState.RUNNING, stop_requested=False)
    assert not can_request_stop(BrowserSessionState.STOPPED, stop_requested=False)
    assert (
        next_state_after_stop_request(BrowserSessionState.RUNNING) == BrowserSessionState.STOPPING
    )
    assert is_terminal(BrowserSessionState.STOPPED)


def test_runtime_seconds():
    start = datetime.now(UTC)
    end = start + timedelta(seconds=42)
    assert runtime_seconds(started_at=start, ended_at=end) == 42


def test_browser_launch_denied_when_not_browser_capable():
    src = _source(connector=ConnectorType.RSS, access=AccessMode.FEED)
    with pytest.raises(BrowserLaunchDenied):
        evaluate_browser_launch(
            src,
            PolicyDecision(runnable=True),
            target_kind=LaunchContextKind.EVENT,
        )


def test_browser_launch_ok_for_browser_connector():
    src = _source()
    engine, reasons = evaluate_browser_launch(
        src,
        PolicyDecision(runnable=True),
        target_kind=LaunchContextKind.EVENT,
    )
    assert engine.value == "playwright"
    assert reasons == ()


def test_browser_launch_cloakbrowser_engine():
    src = _source()
    object.__setattr__(src, "automation_engine", "cloakbrowser")
    engine, _ = evaluate_browser_launch(
        src,
        PolicyDecision(runnable=True),
        target_kind=LaunchContextKind.EVENT,
    )
    assert engine == BrowserEngine.CLOAKBROWSER
