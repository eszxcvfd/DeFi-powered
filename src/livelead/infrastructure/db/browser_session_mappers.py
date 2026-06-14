import json
from uuid import UUID

from livelead.domain.browser.lifecycle import derive_isolation_key, derive_profile_boundary
from livelead.domain.browser.models import (
    BrowserEngine,
    BrowserSessionIsolation,
    BrowserSessionRecord,
    BrowserSessionState,
    BrowserSessionTarget,
    LaunchContextKind,
)
from livelead.infrastructure.db.models import BrowserSessionRow


def row_to_record(row: BrowserSessionRow) -> BrowserSessionRecord:
    reasons = tuple(json.loads(row.policy_reasons_json or "[]"))
    try:
        engine = BrowserEngine(row.engine)
    except ValueError:
        engine = BrowserEngine.PLAYWRIGHT
    return BrowserSessionRecord(
        id=UUID(row.id),
        organization_id=UUID(row.organization_id),
        actor=row.actor,
        state=BrowserSessionState(row.status),
        engine=engine,
        target=BrowserSessionTarget(
            kind=LaunchContextKind(row.launch_kind),
            event_id=UUID(row.event_id) if row.event_id else None,
            source_id=UUID(row.source_id),
            initial_url=row.initial_url,
            source_name=row.source_name,
            source_domain=row.source_domain,
        ),
        isolation=BrowserSessionIsolation(
            isolation_key=row.isolation_key,
            profile_boundary=row.profile_boundary,
            engine=engine,
        ),
        current_url=row.current_url or "",
        latest_action_summary=row.latest_action_summary or "",
        policy_reasons=reasons,
        stop_requested=bool(row.stop_requested),
        error_summary=row.error_summary,
        created_at=row.created_at,
        started_at=row.started_at,
        ended_at=row.ended_at,
        worker_id=row.worker_id,
        debug_enabled=bool(getattr(row, "debug_enabled", False)),
        latest_artifact_summary=getattr(row, "latest_artifact_summary", "") or "",
    )


def new_session_row(
    *,
    organization_id: UUID,
    actor: str,
    target: BrowserSessionTarget,
    engine: BrowserEngine,
    session_id: UUID | None = None,
    browser_profile_id: UUID | None = None,
    isolation_key: str | None = None,
    profile_boundary: str | None = None,
) -> BrowserSessionRow:
    from uuid import uuid4

    sid = str(session_id or uuid4())
    org = str(organization_id)
    return BrowserSessionRow(
        id=sid,
        organization_id=org,
        actor=actor,
        launch_kind=target.kind.value,
        event_id=str(target.event_id) if target.event_id else None,
        source_id=str(target.source_id),
        initial_url=target.initial_url,
        source_name=target.source_name,
        source_domain=target.source_domain,
        engine=engine.value,
        status=BrowserSessionState.QUEUED.value,
        isolation_key=isolation_key or derive_isolation_key(org, sid),
        profile_boundary=profile_boundary or derive_profile_boundary(org, sid),
        browser_profile_id=str(browser_profile_id) if browser_profile_id else None,
        current_url="",
        latest_action_summary="Session queued",
        policy_reasons_json="[]",
        stop_requested=False,
    )
