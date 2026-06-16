"""Discovery job orchestration — uses sync DB in worker thread."""

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from livelead.application.discovery.effective_keywords import keywords_from_criteria_snapshot
from livelead.domain.discovery.browser_recipe import parse_browser_discovery_recipe
from livelead.domain.discovery.browser_source_readiness import (
    browser_execution_mode,
    resolve_browser_discovery_run,
)
from livelead.domain.discovery.lifecycle import aggregate_job_status
from livelead.domain.discovery.live_source_readiness import resolve_live_source_run
from livelead.domain.discovery.models import DiscoveryJobStatus, SourceRunStatus
from livelead.domain.sources.models import ConnectorType
from livelead.domain.sources.policy import evaluate_source_policy
from livelead.infrastructure.connectors.browser_discovery import run_browser_discovery_connector
from livelead.infrastructure.connectors.runner import run_source_connector
from livelead.infrastructure.db.models import Base, DiscoveryJobRow, SourceRow
from livelead.infrastructure.db.source_mappers import row_to_source
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

        settings = parse_settings()
        if settings.discovery_use_mock_connectors:
            logger.warning(
                "discovery_mock_connectors_enabled job_id=%s — set LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS=false and restart worker for real feeds",
                job_id,
            )
        snapshot = json.loads(row.criteria_snapshot_json or "{}")
        source_ids = snapshot.get("source_ids", [])
        sources_progress = progress.get("sources", {})
        source_findings: dict[str, list] = {}
        positive, exclude = keywords_from_criteria_snapshot(
            session, row.campaign_id, row.criteria_snapshot_json or "{}"
        )

        for sid in source_ids:
            session.refresh(row)
            if row.cancel_requested:
                break
            src_row = session.execute(
                select(SourceRow).where(SourceRow.id == sid)
            ).scalar_one_or_none()
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

            use_mock = settings.discovery_use_mock_connectors or domain.lower().endswith(
                "mock.example.com"
            )
            if use_mock and not settings.discovery_use_mock_connectors:
                logger.info("discovery_mock_domain_fixture domain=%s source_id=%s", domain, sid)

            governance = row_to_source(src_row)
            policy_decision = evaluate_source_policy(governance)
            is_browser = governance.connector_type == ConnectorType.BROWSER
            if is_browser:
                pre_status, pre_err, connector_family = resolve_browser_discovery_run(
                    governance,
                    policy_decision,
                    rate_limit_json=src_row.rate_limit_json,
                )
                execution_mode = browser_execution_mode(
                    use_mock=use_mock,
                    automation_engine=governance.automation_engine,
                )
            else:
                pre_status, pre_err, connector_family = resolve_live_source_run(
                    governance, policy_decision
                )
                execution_mode = "mock" if use_mock else "live_feed_api"
            if pre_status != SourceRunStatus.PENDING:
                result_status = pre_status
                result_items = 0
                result_pages = 0
                result_err = pre_err
                findings = []
            elif is_browser:
                recipe, _ = parse_browser_discovery_recipe(src_row.rate_limit_json)
                assert recipe is not None
                mock_result, findings = run_browser_discovery_connector(
                    domain=domain,
                    recipe=recipe,
                    positive_keywords=positive,
                    exclude_keywords=exclude,
                    cancel_check=cancel_check,
                    use_mock_connectors=use_mock,
                    automation_engine=governance.automation_engine,
                    settings=settings,
                )
                result_status = mock_result.status
                result_items = mock_result.items_found
                result_pages = mock_result.pages_processed
                result_err = mock_result.error_summary
            else:
                mock_result, findings = run_source_connector(
                    connector_type=src_row.connector_type,
                    domain=domain,
                    rate_limit_json=src_row.rate_limit_json,
                    positive_keywords=positive,
                    exclude_keywords=exclude,
                    cancel_check=cancel_check,
                    use_mock_connectors=use_mock,
                )
                result_status = mock_result.status
                result_items = mock_result.items_found
                result_pages = mock_result.pages_processed
                result_err = mock_result.error_summary
            if findings:
                source_findings[sid] = findings
            sources_progress[sid] = {
                "status": result_status.value,
                "items_found": result_items,
                "pages_processed": result_pages,
                "error": result_err,
                "connector_family": connector_family,
                "execution_mode": execution_mode,
            }
            progress["sources"] = sources_progress
            progress["events"].append(
                {
                    "type": "job.source_progress",
                    "source_id": sid,
                    "status": result_status.value,
                    "items_found": result_items,
                }
            )
            if result_status == SourceRunStatus.NEEDS_USER_ACTION:
                progress["events"].append({"type": "job.needs_user_action", "source_id": sid})
            _save_progress(row, progress, session)

        session.refresh(row)

        def _to_status(raw: str) -> SourceRunStatus:
            try:
                return SourceRunStatus(raw)
            except ValueError:
                return SourceRunStatus.PENDING

        source_statuses = [
            _to_status(sources_progress.get(sid, {}).get("status", "pending")) for sid in source_ids
        ]
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
                src_row = session.execute(
                    select(SourceRow).where(SourceRow.id == sid)
                ).scalar_one_or_none()
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
                source_findings=source_findings,
            )
            if created:
                score_campaign_events_sync(row.campaign_id, row.organization_id)
    finally:
        session.close()
