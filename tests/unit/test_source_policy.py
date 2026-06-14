from datetime import UTC, datetime
from uuid import uuid4

from livelead.domain.sources.models import (
    AccessMode,
    AuthenticationMode,
    ConnectorType,
    SourceGovernance,
    SourcePolicy,
)
from livelead.domain.sources.policy import evaluate_source_policy, prefer_connector_type
from livelead.infrastructure.secrets.vault import redact_secret


def _source(**kwargs) -> SourceGovernance:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid4(),
        organization_id=uuid4(),
        name="Test",
        domain="example.com",
        connector_type=ConnectorType.RSS,
        automation_engine="none",
        authentication_mode=AuthenticationMode.NONE,
        enabled=True,
        approved=True,
        approved_at=now,
        approved_by="admin",
        policy=SourcePolicy(access_mode=AccessMode.FEED, quota_per_day=10, quota_used_today=0),
        has_secret=False,
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    return SourceGovernance(**defaults)


def test_runnable_when_approved_and_in_window():
    d = evaluate_source_policy(_source(), now=datetime(2026, 6, 13, 12, 0, tzinfo=UTC))
    assert d.runnable
    assert d.preferred_over_browser


def test_denied_when_disabled():
    d = evaluate_source_policy(_source(enabled=False))
    assert not d.runnable
    assert "disabled" in d.reasons


def test_denied_over_quota():
    policy = SourcePolicy(access_mode=AccessMode.FEED, quota_per_day=5, quota_used_today=5)
    d = evaluate_source_policy(_source(policy=policy))
    assert "over_quota" in d.reasons


def test_prefer_api_over_browser():
    assert prefer_connector_type(ConnectorType.RSS, ConnectorType.BROWSER) == ConnectorType.RSS


def test_redact_secret():
    assert redact_secret("super-secret") == "***REDACTED***"