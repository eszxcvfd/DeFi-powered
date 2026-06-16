from datetime import UTC, datetime
from uuid import uuid4

from livelead.domain.discovery.browser_source_readiness import resolve_browser_discovery_run
from livelead.domain.discovery.models import SourceRunStatus
from livelead.domain.sources.models import (
    AccessMode,
    AuthenticationMode,
    ConnectorType,
    PolicyDecision,
    SourceGovernance,
    SourcePolicy,
)


def _source(**kwargs) -> SourceGovernance:
    base = dict(
        id=uuid4(),
        organization_id=uuid4(),
        name="Web",
        domain="site.test",
        connector_type=ConnectorType.BROWSER,
        automation_engine="playwright",
        authentication_mode=AuthenticationMode.NONE,
        enabled=True,
        approved=True,
        approved_at=None,
        approved_by=None,
        policy=SourcePolicy(access_mode=AccessMode.BROWSER, valid=True),
        has_secret=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    base.update(kwargs)
    return SourceGovernance(**base)


def test_runnable_with_valid_recipe():
    rate = '{"browser_discovery_recipe": {"start_url": "https://site.test/", "item_selector": ".e"}}'
    status, err, family = resolve_browser_discovery_run(
        _source(), PolicyDecision(runnable=True), rate_limit_json=rate
    )
    assert status == SourceRunStatus.PENDING
    assert err is None
    assert family == "playwright_website"


def test_selenium_engine_runnable_with_valid_recipe():
    rate = '{"browser_discovery_recipe": {"start_url": "https://site.test/", "item_selector": ".e"}}'
    status, err, family = resolve_browser_discovery_run(
        _source(automation_engine="selenium"),
        PolicyDecision(runnable=True),
        rate_limit_json=rate,
    )
    assert status == SourceRunStatus.PENDING
    assert err is None
    assert family == "selenium_website"


def test_policy_denied():
    status, err, _ = resolve_browser_discovery_run(
        _source(),
        PolicyDecision(runnable=False, reasons=("disabled",)),
        rate_limit_json='{"browser_discovery_recipe": {"start_url": "https://x", "item_selector": ".a"}}',
    )
    assert status == SourceRunStatus.FAILED
    assert err == "policy_denied:disabled"


def test_recipe_not_ready():
    status, err, _ = resolve_browser_discovery_run(
        _source(), PolicyDecision(runnable=True), rate_limit_json="{}"
    )
    assert status == SourceRunStatus.FAILED
    assert err and err.startswith("recipe_not_ready:")


def test_session_auth_needs_user_action():
    status, err, _ = resolve_browser_discovery_run(
        _source(authentication_mode=AuthenticationMode.SESSION),
        PolicyDecision(runnable=True),
        rate_limit_json='{"browser_discovery_recipe": {"start_url": "https://x", "item_selector": ".a"}}',
    )
    assert status == SourceRunStatus.NEEDS_USER_ACTION
    assert "login" in (err or "")