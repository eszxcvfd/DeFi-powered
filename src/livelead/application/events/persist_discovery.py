"""Persist normalized events after discovery (sync worker session)."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import mock_findings_for_items
from livelead.infrastructure.db.models import Base, SourceRow
from livelead.runtime.settings import parse_settings

logger = logging.getLogger("livelead.events")


def _sync_session() -> Session:
    settings = parse_settings()
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def persist_events_from_discovery_job(
    *,
    job_id: str,
    organization_id: str,
    campaign_id: str,
    sources_progress: dict,
    source_id_to_domain: dict[str, str],
) -> int:
    """Normalize findings with deduplication. Returns count of new canonical events."""
    session = _sync_session()
    created = 0
    merged = 0
    try:
        org = UUID(organization_id)
        camp = UUID(campaign_id)
        for sid, prog in sources_progress.items():
            items = int(prog.get("items_found") or 0)
            if items <= 0:
                continue
            domain = source_id_to_domain.get(sid, "events.example.com")
            source_uuid = UUID(sid)
            for finding in mock_findings_for_items(items, domain, source_uuid):
                eid, action = ingest_finding(
                    session,
                    organization_id=org,
                    campaign_id=camp,
                    source_id=source_uuid,
                    finding=finding,
                    discovery_job_id=job_id,
                )
                if action == "created":
                    created += 1
                elif action == "merged":
                    merged += 1
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


def load_source_domains(session: Session, source_ids: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for sid in source_ids:
        row = session.execute(select(SourceRow).where(SourceRow.id == sid)).scalar_one_or_none()
        if row:
            out[sid] = row.domain
    return out


def score_campaign_events_sync(campaign_id: str, organization_id: str) -> int:
    from livelead.application.scoring.sync_score import score_all_for_campaign_sync

    return score_all_for_campaign_sync(campaign_id, organization_id)