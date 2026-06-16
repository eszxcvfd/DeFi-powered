"""Scheduler-driven dispatch for discovery schedules (US-035)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from livelead.application.query_expansion.criteria import build_discovery_criteria
from livelead.domain.discovery.schedule_recurrence import compute_next_run, parse_recurrence
from livelead.domain.discovery.schedule_state import schedule_may_dispatch, should_skip_overlap
from livelead.domain.sources.policy import evaluate_source_policy
from livelead.infrastructure.db.models import (
    Base,
    CampaignRow,
    DiscoveryJobRow,
    DiscoveryScheduleDispatchRow,
    DiscoveryScheduleRow,
    SourceRow,
)
from livelead.infrastructure.db.source_mappers import row_to_source
from livelead.runtime.settings import parse_settings

logger = logging.getLogger("livelead.scheduler.dispatch")


def _sync_session() -> Session:
    settings = parse_settings()
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _active_job_status(session: Session, job_id: str | None) -> str | None:
    if not job_id:
        return None
    row = session.get(DiscoveryJobRow, job_id)
    return row.status if row else None


def _sources_runnable(session: Session, org_id: str, source_ids: list[str]) -> tuple[bool, str | None]:
    for sid in source_ids:
        row = session.get(SourceRow, sid)
        if not row or row.organization_id != org_id:
            return False, f"source missing: {sid}"
        d = evaluate_source_policy(row_to_source(row))
        if not d.runnable:
            return False, f"policy blocked: {sid}"
    return True, None


def _record_dispatch(
    session: Session,
    *,
    org_id: str,
    schedule_id: str,
    outcome: str,
    job_id: str | None,
    detail: str | None,
) -> None:
    session.add(
        DiscoveryScheduleDispatchRow(
            id=str(uuid4()),
            organization_id=org_id,
            schedule_id=schedule_id,
            outcome=outcome,
            discovery_job_id=job_id,
            detail=detail,
            created_at=datetime.now(UTC),
        )
    )


def dispatch_due_schedules(*, now: datetime | None = None, enqueue: bool = True) -> list[dict]:
    """Scan enabled schedules with next_run_at <= now and dispatch or skip safely."""
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    session = _sync_session()
    outcomes: list[dict] = []
    try:
        stmt = (
            select(DiscoveryScheduleRow)
            .where(DiscoveryScheduleRow.enabled_state == "enabled")
            .where(DiscoveryScheduleRow.next_run_at.is_not(None))
            .where(DiscoveryScheduleRow.next_run_at <= now)
            .order_by(DiscoveryScheduleRow.next_run_at)
            .limit(50)
        )
        due = list(session.execute(stmt).scalars().all())

        for sched in due:
            if not schedule_may_dispatch(sched.enabled_state):
                continue

            spec = parse_recurrence(json.loads(sched.recurrence_json))
            source_ids = json.loads(sched.source_ids_json or "[]")

            if should_skip_overlap(active_job_status=_active_job_status(session, sched.last_dispatched_job_id)):
                sched.last_dispatch_outcome = "skipped_overlap"
                _record_dispatch(
                    session,
                    org_id=sched.organization_id,
                    schedule_id=sched.id,
                    outcome="skipped_overlap",
                    job_id=None,
                    detail="skip_while_running",
                )
                sched.next_run_at = compute_next_run(spec, after=now)
                outcomes.append({"schedule_id": sched.id, "outcome": "skipped_overlap"})
                continue

            ok, block = _sources_runnable(session, sched.organization_id, source_ids)
            if not ok:
                sched.last_dispatch_outcome = "blocked_policy"
                _record_dispatch(
                    session,
                    org_id=sched.organization_id,
                    schedule_id=sched.id,
                    outcome="blocked_policy",
                    job_id=None,
                    detail=block,
                )
                sched.next_run_at = compute_next_run(spec, after=now)
                outcomes.append({"schedule_id": sched.id, "outcome": "blocked_policy", "detail": block})
                continue

            camp = session.get(CampaignRow, sched.campaign_id)
            if not camp or camp.organization_id != sched.organization_id:
                sched.last_dispatch_outcome = "blocked_campaign"
                _record_dispatch(
                    session,
                    org_id=sched.organization_id,
                    schedule_id=sched.id,
                    outcome="blocked_campaign",
                    job_id=None,
                    detail="campaign missing",
                )
                sched.next_run_at = compute_next_run(spec, after=now)
                outcomes.append({"schedule_id": sched.id, "outcome": "blocked_campaign"})
                continue

            from livelead.application.query_expansion.service import QueryExpansionBlockedError

            try:
                criteria = build_discovery_criteria(
                    session,
                    camp,
                    campaign_id=UUID(sched.campaign_id),
                    source_ids=source_ids,
                    organization_id=UUID(sched.organization_id),
                    schedule_id=sched.id,
                    use_expansion=True,
                )
            except QueryExpansionBlockedError as exc:
                sched.last_dispatch_outcome = "blocked_query_expansion"
                _record_dispatch(
                    session,
                    org_id=sched.organization_id,
                    schedule_id=sched.id,
                    outcome="blocked_query_expansion",
                    job_id=None,
                    detail=str(exc),
                )
                sched.next_run_at = compute_next_run(spec, after=now)
                outcomes.append({"schedule_id": sched.id, "outcome": "blocked_query_expansion"})
                continue
            from livelead.domain.discovery.models import DiscoveryJobStatus

            # sync job create inline (mirror async repository logic)
            progress = {
                "percent": 0,
                "sources": {
                    sid: {"status": "pending", "items_found": 0, "pages_processed": 0}
                    for sid in source_ids
                },
                "events": [{"type": "job.queued", "at": now.isoformat(), "trigger": "scheduled"}],
            }
            job = DiscoveryJobRow(
                id=str(uuid4()),
                organization_id=sched.organization_id,
                campaign_id=sched.campaign_id,
                status=DiscoveryJobStatus.QUEUED.value,
                criteria_snapshot_json=json.dumps(criteria),
                progress_json=json.dumps(progress),
                discovery_schedule_id=sched.id,
                created_by="scheduler",
                created_at=now,
            )
            session.add(job)
            session.flush()

            sched.last_dispatched_job_id = job.id
            sched.last_dispatch_outcome = "job_created"
            _record_dispatch(
                session,
                org_id=sched.organization_id,
                schedule_id=sched.id,
                outcome="job_created",
                job_id=job.id,
                detail=None,
            )
            sched.next_run_at = compute_next_run(spec, after=now)

            if enqueue:
                try:
                    import apps.worker.discovery_tasks as discovery_tasks

                    discovery_tasks.run_discovery_job.send(job.id)
                except Exception as exc:
                    job.status = DiscoveryJobStatus.FAILED.value
                    job.completed_at = datetime.now(UTC)
                    job.error_summary = f"Queue connection failed: {exc}"
                    sched.last_dispatch_outcome = "queue_failed"
                    logger.warning("schedule_dispatch_queue_failed schedule=%s err=%s", sched.id, exc)

            outcomes.append({"schedule_id": sched.id, "outcome": "job_created", "job_id": job.id})
            logger.info(
                "schedule_dispatched schedule_id=%s job_id=%s campaign_id=%s",
                sched.id,
                job.id,
                sched.campaign_id,
            )

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return outcomes