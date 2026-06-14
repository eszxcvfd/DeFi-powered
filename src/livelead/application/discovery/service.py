"""Discovery job orchestration — uses sync DB in worker thread."""

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from livelead.domain.discovery.lifecycle import aggregate_job_status
from livelead.domain.discovery.models import DiscoveryJobStatus, SourceRunStatus
from livelead.infrastructure.connectors.mock import run_mock_source
from livelead.infrastructure.db.models import Base, DiscoveryJobRow, SourceRow
from livelead.runtime.settings import parse_settings

logger = logging.getLogger("livelead.discovery")


def _sync_session() -> Session:
    settings = parse_settings()
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _load_progress(row: DiscoveryJobRow) -> dict:
    return json.loads(row.progress_json or "{}")


def _save_progress(row: DiscoveryJobRow, progress: dict, session: Session) -> None:
    row.progress_json = json.dumps(progress)
    session.add(row)
    session.commit()


def run_discovery_job(job_id: str) -> None:
    session = _sync_session()
    try:
        row = session.get(DiscoveryJobRow, job_id)
        if not row:
            logger.warning("discovery_job_missing job_id=%s", job_id)
            return
        if row.cancel_requested:
            row.status = DiscoveryJobStatus.CANCELLED.value
            row.completed_at = datetime.now(UTC)
            session.commit()
            return

        row.status = DiscoveryJobStatus.RUNNING.value
        row.started_at = datetime.now(UTC)
        progress = _load_progress(row)
        progress["events"] = progress.get("events", [])
        progress["events"].append({"type": "job.started", "at": datetime.now(UTC).isoformat()})
        _save_progress(row, progress, session)

        snapshot = json.loads(row.criteria_snapshot_json or "{}")
        source_ids = snapshot.get("source_ids", [])
        sources_progress = progress.get("sources", {})

        for sid in source_ids:
            session.refresh(row)
            if row.cancel_requested:
                break
            src_row = session.execute(select(SourceRow).where(SourceRow.id == sid)).scalar_one_or_none()
            if not src_row:
                continue
            domain = src_row.domain
            sources_progress[sid] = {
                "status": SourceRunStatus.RUNNING.value,
                "items_found": 0,
                "pages_processed": 0,
            }
            progress["sources"] = sources_progress
            progress["events"].append(
                {"type": "job.source_progress", "source_id": sid, "status": "running"}
            )
            _save_progress(row, progress, session)

            def cancel_check() -> bool:
                session.refresh(row)
                return bool(row.cancel_requested)

            result = run_mock_source(domain, cancel_check=cancel_check)
            sources_progress[sid] = {
                "status": result.status.value,
                "items_found": result.items_found,
                "pages_processed": result.pages_processed,
                "error": result.error_summary,
            }
            progress["sources"] = sources_progress
            progress["events"].append(
                {
                    "type": "job.source_progress",
                    "source_id": sid,
                    "status": result.status.value,
                    "items_found": result.items_found,
                }
            )
            if result.status == SourceRunStatus.NEEDS_USER_ACTION:
                progress["events"].append({"type": "job.needs_user_action", "source_id": sid})
            _save_progress(row, progress, session)

        session.refresh(row)
        def _to_status(raw: str) -> SourceRunStatus:
            try:
                return SourceRunStatus(raw)
            except ValueError:
                return SourceRunStatus.PENDING

        source_statuses = [_to_status(sources_progress.get(sid, {}).get("status", "pending")) for sid in source_ids]
        final = aggregate_job_status(source_statuses, cancelled=bool(row.cancel_requested))
        row.status = final.value
        row.completed_at = datetime.now(UTC)
        if final == DiscoveryJobStatus.FAILED:
            row.error_summary = "all_sources_failed"
            progress["events"].append({"type": "job.failed"})
        elif final == DiscoveryJobStatus.CANCELLED:
            progress["events"].append({"type": "job.completed", "note": "cancelled"})
        else:
            progress["events"].append({"type": "job.completed", "status": final.value})
        progress["percent"] = 100
        row.progress_json = json.dumps(progress)
        session.commit()
        logger.info("discovery_job_terminal job_id=%s status=%s", job_id, final.value)

        if final != DiscoveryJobStatus.CANCELLED:
            domain_map: dict[str, str] = {}
            for sid in source_ids:
                src_row = session.execute(select(SourceRow).where(SourceRow.id == sid)).scalar_one_or_none()
                if src_row:
                    domain_map[sid] = src_row.domain
            from livelead.application.events.persist_discovery import (
                persist_events_from_discovery_job,
                score_campaign_events_sync,
            )

            created = persist_events_from_discovery_job(
                job_id=job_id,
                organization_id=row.organization_id,
                campaign_id=row.campaign_id,
                sources_progress=sources_progress,
                source_id_to_domain=domain_map,
            )
            if created:
                score_campaign_events_sync(row.campaign_id, row.organization_id)
    finally:
        session.close()