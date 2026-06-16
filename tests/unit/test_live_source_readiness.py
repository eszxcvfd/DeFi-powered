from datetime import UTC, datetime

from livelead.domain.discovery.live_source_readiness import (
    live_connector_family,
    resolve_live_source_run,
)
from livelead.domain.discovery.models import SourceRunStatus
from livelead.domain.sources.models import (
    AccessMode,
    AuthenticationMode,
    ConnectorType,
    PolicyDecision,
    SourceGovernance,
    SourcePolicy,
)
from uuid import uuid4


def _source(**kwargs) -> SourceGovernance:
    base = dict(
        id=uuid4(),
        organization_id=uuid4(),
        name="Feed",
        domain="feed.test",
        connector_type=ConnectorType.RSS,
        automation_engine="none",
        authentication_mode=AuthenticationMode.NONE,
        enabled=True,
        approved=True,
        approved_at=None,
        approved_by=None,
        policy=SourcePolicy(access_mode=AccessMode.FEED, valid=True),
        has_secret=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    base.update(kwargs)
    return SourceGovernance(**base)


def test_runnable_rss_pending():
    d = PolicyDecision(runnable=True, reasons=(), preferred_over_browser=True)
    status, err, family = resolve_live_source_run(_source(), d)
    assert status == SourceRunStatus.PENDING
    assert err is None
    assert family == "rss_atom"


def test_policy_denied_blocks_fetch():
    d = PolicyDecision(runnable=False, reasons=("over_quota",), preferred_over_browser=False)
    status, err, _ = resolve_live_source_run(_source(), d)
    assert status == SourceRunStatus.FAILED
    assert err == "policy_denied:over_quota"


def test_browser_routes_to_playwright_discovery_path():
    d = PolicyDecision(runnable=True, reasons=(), preferred_over_browser=False)
    status, err, family = resolve_live_source_run(
        _source(connector_type=ConnectorType.BROWSER), d
    )
    assert status == SourceRunStatus.FAILED
    assert "playwright" in (err or "")
    assert family == "playwright_website"


def test_ics_family():
    assert live_connector_family(ConnectorType.ICS) == "ics"