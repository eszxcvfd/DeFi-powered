"""Persist normalized events after discovery (sync worker session)."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from livelead.application.events.finding_adapter import to_ingest_finding
from livelead.application.events.ingest import ingest_finding
from livelead.domain.discovery.finding import DiscoveryFinding
from livelead.domain.events.normalize import MockFinding
from livelead.infrastructure.db.models import Base
from livelead.runtime.settings import parse_settings

logger = logging.getLogger("livelead.events")


def _sync_session() -> Session:
    settings = parse_settings()
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _ingest_many(
    session: Session,
    *,
    org: UUID,
    camp: UUID,
    sid: str,
    job_id: str,
    findings: list[MockFinding],
) -> tuple[int, int]:
    created = merged = 0
    for finding in findings:
        _, action = ingest_finding(
            session,
            organization_id=org,
            campaign_id=camp,
            source_id=UUID(sid),
            finding=finding,
            discovery_job_id=job_id,
        )
        if action == "created":
            created += 1
        elif action == "merged":
            merged += 1
    return created, merged


def persist_events_from_discovery_job(
    *,
    job_id: str,
    organization_id: str,
    campaign_id: str,
    sources_progress: dict,
    source_id_to_domain: dict[str, str],
    source_findings: dict[str, list[DiscoveryFinding]] | None = None,
) -> int:
    session = _sync_session()
    created = 0
    merged = 0
    source_findings = source_findings or {}
    try:
        org = UUID(organization_id)
        camp = UUID(campaign_id)
        for sid, prog in sources_progress.items():
            real = source_findings.get(sid) or []
            if not real:
                items = int(prog.get("items_found") or 0)
                if items > 0:
                    logger.warning(
                        "discovery_items_without_findings job_id=%s source_id=%s items_found=%s",
                        job_id,
                        sid,
                        items,
                    )
                continue
            c, m = _ingest_many(
                session,
                org=org,
                camp=camp,
                sid=sid,
                job_id=job_id,
                findings=[to_ingest_finding(f) for f in real],
            )
            created += c
            merged += m
        session.commit()
        if created or merged:
            logger.info(
                "discovery_events_normalized job_id=%s campaign_id=%s created=%s merged=%s",
                job_id,
                campaign_id,
                created,
                merged,
            )
    finally:
        session.close()
    return created


def score_campaign_events_sync(campaign_id: str, organization_id: str) -> int:
    from livelead.application.scoring.sync_score import score_all_for_campaign_sync

    return score_all_for_campaign_sync(campaign_id, organization_id)
