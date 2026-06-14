"""Persist Playwright browser source + campaign link from event evidence (no Admin UI)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.browser.evidence_provisioning import (
    auto_provision_domain,
    playwright_connector_name,
)
from livelead.domain.sources.models import (
    AccessMode,
    AuthenticationMode,
    ConnectorType,
    SourceGovernance,
    SourcePolicy,
)
from livelead.infrastructure.db.repositories.sources import SourceRepository

logger = logging.getLogger("livelead.browser_evidence")


async def ensure_playwright_source_for_event(
    session: AsyncSession,
    *,
    organization_id: UUID,
    campaign_id: UUID,
    actor: str,
    event_source_url: str,
    observation_urls: list[str],
) -> SourceGovernance | None:
    domain = auto_provision_domain(event_source_url, observation_urls)
    if not domain:
        return None

    repo = SourceRepository(session)
    existing = await repo.list_for_organization(organization_id)
    for src in existing:
        if src.connector_type == ConnectorType.BROWSER and src.domain.lower() == domain:
            await _link_campaign_source(repo, campaign_id, organization_id, src.id)
            return src

    row = SourceRepository.new_row(
        organization_id,
        {
            "name": playwright_connector_name(domain),
            "domain": domain,
            "connector_type": ConnectorType.BROWSER.value,
            "automation_engine": "playwright",
            "authentication_mode": AuthenticationMode.NONE.value,
            "enabled": True,
            "approved": True,
            "approved_by": actor,
            "approved_at": datetime.now(UTC),
            "policy": SourcePolicy(access_mode=AccessMode.BROWSER, valid=True),
            "secret_ciphertext": None,
        },
    )
    created = await repo.add(row)
    await _link_campaign_source(repo, campaign_id, organization_id, created.id)
    logger.info(
        "browser_evidence_provisioned org=%s campaign=%s domain=%s source_id=%s",
        organization_id,
        campaign_id,
        domain,
        created.id,
    )
    return created


async def _link_campaign_source(
    repo: SourceRepository,
    campaign_id: UUID,
    organization_id: UUID,
    source_id: UUID,
) -> None:
    ids = await repo.list_campaign_source_ids(campaign_id, organization_id)
    if source_id in ids:
        return
    await repo.set_campaign_sources(campaign_id, organization_id, [*ids, source_id])
