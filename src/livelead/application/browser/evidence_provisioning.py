"""Persist browser sources + campaign link from event evidence (no Admin UI)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.browser.evidence_provisioning import (
    EVIDENCE_BROWSER_ENGINES,
    auto_provision_domain,
    browser_connector_name,
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


async def ensure_browser_sources_for_event(
    session: AsyncSession,
    *,
    organization_id: UUID,
    campaign_id: UUID,
    actor: str,
    event_source_url: str,
    observation_urls: list[str],
) -> list[SourceGovernance]:
    domain = auto_provision_domain(event_source_url, observation_urls)
    if not domain:
        return []

    repo = SourceRepository(session)
    existing = await repo.list_for_organization(organization_id)
    by_domain_engine: dict[tuple[str, str], SourceGovernance] = {}
    for src in existing:
        if src.connector_type != ConnectorType.BROWSER:
            continue
        eng = (src.automation_engine or "playwright").lower()
        by_domain_engine[(src.domain.lower(), eng)] = src

    created_or_linked: list[SourceGovernance] = []
    for engine in EVIDENCE_BROWSER_ENGINES:
        key = (domain, engine)
        src = by_domain_engine.get(key)
        if src is None:
            row = SourceRepository.new_row(
                organization_id,
                {
                    "name": browser_connector_name(domain, engine),
                    "domain": domain,
                    "connector_type": ConnectorType.BROWSER.value,
                    "automation_engine": engine,
                    "authentication_mode": AuthenticationMode.NONE.value,
                    "enabled": True,
                    "approved": True,
                    "approved_by": actor,
                    "approved_at": datetime.now(UTC),
                    "policy": SourcePolicy(access_mode=AccessMode.BROWSER, valid=True),
                    "secret_ciphertext": None,
                },
            )
            src = await repo.add(row)
            logger.info(
                "browser_evidence_provisioned org=%s campaign=%s domain=%s engine=%s source_id=%s",
                organization_id,
                campaign_id,
                domain,
                engine,
                src.id,
            )
        await _link_campaign_source(repo, campaign_id, organization_id, src.id)
        created_or_linked.append(src)

    return created_or_linked


async def ensure_playwright_source_for_event(
    session: AsyncSession,
    *,
    organization_id: UUID,
    campaign_id: UUID,
    actor: str,
    event_source_url: str,
    observation_urls: list[str],
) -> SourceGovernance | None:
    """Backward-compatible entry: returns first provisioned source (Playwright when created)."""
    sources = await ensure_browser_sources_for_event(
        session,
        organization_id=organization_id,
        campaign_id=campaign_id,
        actor=actor,
        event_source_url=event_source_url,
        observation_urls=observation_urls,
    )
    if not sources:
        return None
    for src in sources:
        if (src.automation_engine or "").lower() == "playwright":
            return src
    return sources[0]


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