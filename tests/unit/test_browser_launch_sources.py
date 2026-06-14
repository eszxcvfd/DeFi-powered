from datetime import UTC, datetime
from uuid import uuid4

from livelead.domain.browser.launch_sources import (
    pick_browser_source_for_event,
    source_allows_browser_launch,
)
from livelead.domain.sources.models import (
    AccessMode,
    AuthenticationMode,
    ConnectorType,
    SourceGovernance,
    SourcePolicy,
)


def _src(connector=ConnectorType.BROWSER, engine="cloakbrowser"):
    now = datetime.now(UTC)
    return SourceGovernance(
        id=uuid4(),
        organization_id=uuid4(),
        name="Cloak source",
        domain="partners.example.com",
        connector_type=connector,
        automation_engine=engine,
        authentication_mode=AuthenticationMode.NONE,
        enabled=True,
        approved=True,
        approved_at=now,
        approved_by="admin",
        policy=SourcePolicy(access_mode=AccessMode.BROWSER, valid=True),
        has_secret=False,
        created_at=now,
        updated_at=now,
    )


def test_pick_falls_back_when_observation_source_missing_from_registry():
    live = _src()
    stale = uuid4()
    picked = pick_browser_source_for_event(
        observation_source_ids=[stale],
        campaign_source_ids=[live.id],
        registry={live.id: live},
    )
    assert picked == live.id


def test_cloakbrowser_connector_allowed():
    assert source_allows_browser_launch(_src(engine="cloakbrowser"))
