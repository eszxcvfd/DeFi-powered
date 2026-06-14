import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.discovery.lifecycle import is_terminal
from livelead.domain.discovery.models import DiscoveryJobStatus
from livelead.domain.sources.policy import evaluate_source_policy
from livelead.infrastructure.db.models import CampaignRow, DiscoveryJobRow
from livelead.infrastructure.db.repositories.discovery_jobs import DiscoveryJobRepository
from livelead.infrastructure.db.repositories.sources import SourceRepository
from livelead.infrastructure.db.source_mappers import row_to_source
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
    require_scoring_editor,
)
from livelead.interfaces.rest.deps import get_db_session

router = APIRouter(tags=["discovery-jobs"])


class DiscoveryJobView(BaseModel):
    id: UUID
    campaign_id: UUID
    status: str
    progress: dict
    error_summary: str | None
    cancel_requested: bool
    criteria_snapshot: dict


def _to_view(row: DiscoveryJobRow) -> DiscoveryJobView:
    return DiscoveryJobView(
        id=UUID(row.id),
        campaign_id=UUID(row.campaign_id),
        status=row.status,
        progress=json.loads(row.progress_json or "{}"),
        error_summary=row.error_summary,
        cancel_requested=bool(row.cancel_requested),
        criteria_snapshot=json.loads(row.criteria_snapshot_json or "{}"),
    )


@router.post("/campaigns/{campaign_id}/discovery-jobs", response_model=DiscoveryJobView, status_code=201)
async def create_discovery_job(
    campaign_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    camp = await session.execute(
        select(CampaignRow).where(
            CampaignRow.id == str(campaign_id),
            CampaignRow.organization_id == str(tenant.organization_id),
        )
    )
    camp_row = camp.scalar_one_or_none()
    if not camp_row:
        raise HTTPException(status_code=404, detail="campaign not found")

    src_repo = SourceRepository(session)
    source_ids = await src_repo.list_campaign_source_ids(campaign_id, tenant.organization_id)
    if not source_ids:
        all_src = await src_repo.list_for_organization(tenant.organization_id)
        runnable = [s for s in all_src if evaluate_source_policy(s).runnable]
        if not runnable:
            raise HTTPException(status_code=409, detail="no runnable sources")
        source_ids = [runnable[0].id]

    for sid in source_ids:
        row = await src_repo.get(sid, tenant.organization_id)
        if not row:
            raise HTTPException(status_code=404, detail="source missing")
        d = evaluate_source_policy(row_to_source(row))
        if not d.runnable:
            raise HTTPException(status_code=409, detail={"policy_denied": list(d.reasons), "source_id": str(sid)})

    import json as _json

    criteria = {
        "campaign_id": str(campaign_id),
        "campaign_name": camp_row.name,
        "source_ids": [str(s) for s in source_ids],
        "positive_keywords": _json.loads(camp_row.positive_keywords_json or "[]"),
        "exclude_keywords": _json.loads(camp_row.exclude_keywords_json or "[]"),
    }
    repo = DiscoveryJobRepository(session)
    job_row = await repo.create(
        organization_id=tenant.organization_id,
        campaign_id=campaign_id,
        criteria_snapshot=criteria,
        source_ids=[str(s) for s in source_ids],
        created_by=tenant.actor_role,
    )
    await session.commit()

    from datetime import UTC, datetime

    import apps.worker.discovery_tasks as discovery_tasks

    try:
        discovery_tasks.run_discovery_job.send(job_row.id)
    except Exception as e:
        job_row.status = "failed"
        job_row.completed_at = datetime.now(UTC)
        job_row.error_summary = f"Queue connection failed: {str(e)}"
        await session.commit()
        raise HTTPException(
            status_code=503,
            detail="Discovery queue service is currently unavailable. Please verify Redis is running.",
        ) from e

    return _to_view(job_row)


@router.get("/discovery-jobs/{job_id}", response_model=DiscoveryJobView)
async def get_discovery_job(
    job_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    repo = DiscoveryJobRepository(session)
    row = await repo.get(job_id, tenant.organization_id)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    return _to_view(row)


@router.post("/discovery-jobs/{job_id}/cancel", response_model=DiscoveryJobView)
async def cancel_discovery_job(
    job_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    repo = DiscoveryJobRepository(session)
    row = await repo.get(job_id, tenant.organization_id)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    if is_terminal(DiscoveryJobStatus(row.status)):
        raise HTTPException(status_code=409, detail="job already terminal")
    row = await repo.request_cancel(row)
    await session.commit()
    return _to_view(row)


@router.get("/discovery-jobs/{job_id}/stream")
async def stream_discovery_job(
    job_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
):
    factory = request.app.state.session_factory

    async def event_gen():
        last_len = 0
        for _ in range(120):
            async with factory() as sess:
                repo2 = DiscoveryJobRepository(sess)
                current = await repo2.get(job_id, tenant.organization_id)
            if not current:
                break
            progress = json.loads(current.progress_json or "{}")
            events = progress.get("events", [])
            for ev in events[last_len:]:
                yield f"data: {json.dumps(ev)}\n\n"
            last_len = len(events)
            yield f"data: {json.dumps({'type': 'job.progress', 'status': current.status, 'percent': progress.get('percent', 0)})}\n\n"
            if is_terminal(DiscoveryJobStatus(current.status)):
                break
            await asyncio.sleep(0.25)
        yield 'data: {"type":"stream.end"}\n\n'

    return StreamingResponse(event_gen(), media_type="text/event-stream")