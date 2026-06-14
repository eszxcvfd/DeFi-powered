from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audience.service import AudienceService
from livelead.application.content.service import ContentService
from livelead.application.engagement.service import EngagementService
from livelead.application.leads.service import LeadService
from livelead.application.scoring.service import ScoringService
from livelead.domain.content.review import is_ready_for_later_use
from livelead.infrastructure.db.repositories.campaigns import CampaignRepository
from livelead.infrastructure.db.repositories.event_scores import EventScoreRepository
from livelead.infrastructure.db.repositories.events import (
    EventRepository,
    provenance_from_metadata_json,
)
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.deps import get_db_session
from livelead.interfaces.rest.events_schemas import (
    AudienceAnalysisSchema,
    AudienceEvidenceSchema,
    AudienceHypothesisSchema,
    EngagementPlanStateSchema,
    EngagementPlanSummarySchema,
    EngagementTaskSchema,
    EngagementTaskUpdateSchema,
    EventDetailSchema,
    EventLeadLinkSchema,
    EventListItemSchema,
    EventProvenanceSchema,
    EventScoreDetailSchema,
    EventScoreSummarySchema,
    EventSourceObservationSchema,
    FieldConfidenceSchema,
    GeneratedContentSummarySchema,
    ScoreComponentSchema,
)

router = APIRouter(tags=["events"])


def _score_summary(score) -> EventScoreSummarySchema:
    if not score:
        return EventScoreSummarySchema(score_state="missing")
    return EventScoreSummarySchema(
        total_score=score.total_score,
        priority_level=score.priority_level.value,
        scoring_version=score.scoring_version,
        calculated_at=score.calculated_at,
        score_state="ready",
    )


def _score_detail(score) -> EventScoreDetailSchema:
    return EventScoreDetailSchema(
        total_score=score.total_score,
        priority_level=score.priority_level.value,
        scoring_version=score.scoring_version,
        calculated_at=score.calculated_at,
        weights_snapshot=score.weights_snapshot,
        components=[
            ScoreComponentSchema(
                key=c.key,
                raw_value=c.raw_value,
                weighted_contribution=c.weighted_contribution,
                evidence=c.evidence,
                missing_data=list(c.missing_data),
            )
            for c in score.components
        ],
        missing_fields=list(score.explanation.missing_fields),
        score_reducers=list(score.explanation.score_reducers),
    )


def _engagement_schema(state) -> EngagementPlanStateSchema:
    plan_schema = None
    if state.plan:
        plan_schema = EngagementPlanSummarySchema(
            id=state.plan.id,
            strategy_version=state.plan.strategy_version,
            created_at=state.plan.created_at,
            updated_at=state.plan.updated_at,
        )
    return EngagementPlanStateSchema(
        state=state.state,
        plan=plan_schema,
        generation_notes=list(state.generation_notes),
        tasks=[
            EngagementTaskSchema(
                id=t.id,
                phase=t.phase.value,
                title=t.title,
                rationale=t.rationale,
                status=t.status.value,
                assignee=t.assignee,
                deadline=t.deadline,
                notes=t.notes,
            )
            for t in state.tasks
        ],
    )


def _audience_schema(analysis) -> AudienceAnalysisSchema:
    return AudienceAnalysisSchema(
        state=analysis.state,
        strategy_version=analysis.strategy_version,
        generation_notes=list(analysis.generation_notes),
        hypotheses=[
            AudienceHypothesisSchema(
                id=h.id,
                segment_name=h.segment_name,
                fit_type=h.fit_type.value,
                reason=h.reason,
                confidence=h.confidence,
                generated_by=h.generated_by,
                model_version=h.model_version,
                evidence=[
                    AudienceEvidenceSchema(
                        cue=e.cue,
                        kind=e.kind.value,
                        detail=e.detail,
                        source_field=e.source_field,
                    )
                    for e in h.evidence
                ],
            )
            for h in analysis.hypotheses
        ],
    )


def _provenance_schema(row, obs_count: int, source_ids: list[UUID]) -> EventProvenanceSchema:
    raw = provenance_from_metadata_json(row.metadata_json if row else "{}")
    return EventProvenanceSchema(
        confidence_summary=raw["confidence_summary"],
        field_confidence=[
            FieldConfidenceSchema(field=f["field"], trust=f["trust"], note=f.get("note", ""))
            for f in raw.get("field_confidence", [])
            if isinstance(f, dict)
        ],
        merge_notes=raw.get("merge_notes", []),
        observation_count=obs_count,
        source_ids=source_ids,
    )


@router.get("/campaigns/{campaign_id}/events", response_model=list[EventListItemSchema])
async def list_campaign_events(
    campaign_id: UUID,
    discovery_job_id: UUID | None = Query(default=None),
    source_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None, max_length=200),
    include_score: bool = Query(default=True),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    campaigns = CampaignRepository(session)
    if not await campaigns.get(campaign_id, tenant.organization_id):
        raise HTTPException(status_code=404, detail="campaign not found")
    events = EventRepository(session)
    rows = await events.list_for_campaign(
        campaign_id,
        tenant.organization_id,
        discovery_job_id=discovery_job_id,
        source_id=source_id,
        q=q,
    )
    counts = await events.observation_counts([e.id for e in rows])
    score_map = {}
    if include_score:
        scores = EventScoreRepository(session)
        score_map = await scores.get_current_for_events([e.id for e in rows], campaign_id)
    source_counts: dict[UUID, int] = {}
    for e in rows:
        src_ids = await events.distinct_source_ids(e.id)
        source_counts[e.id] = len(src_ids) or 1
    await session.commit()
    out: list[EventListItemSchema] = []
    for e in rows:
        obs_n = counts.get(e.id, 1)
        item = EventListItemSchema(
            id=e.id,
            campaign_id=e.campaign_id,
            canonical_title=e.canonical_title,
            source_url=e.source_url,
            observed_at=e.observed_at,
            region=e.region,
            confidence_summary=e.confidence_summary,
            observation_count=obs_n,
            source_count=source_counts.get(e.id, 1),
            discovery_job_id=UUID(e.discovery_job_id) if e.discovery_job_id else None,
            score=_score_summary(score_map.get(e.id)) if include_score else None,
            deferred={"scoring": "available" if include_score else "omitted"},
        )
        out.append(item)
    return out


@router.get("/events/{event_id}", response_model=EventDetailSchema)
async def get_event(
    event_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    events = EventRepository(session)
    event = await events.get(event_id, tenant.organization_id)
    if not event:
        raise HTTPException(status_code=404, detail="event not found")
    row = await events.get_row(event_id, tenant.organization_id)
    obs = await events.list_observations(event_id)
    src_ids = await events.distinct_source_ids(event_id)
    score = await EventScoreRepository(session).get_current(event_id, event.campaign_id)
    audience = await AudienceService(session).get_or_generate(event_id, tenant.organization_id)
    engagement = await EngagementService(session).get_plan_state(event_id, tenant.organization_id)
    draft_list = await ContentService(session).list_drafts(event_id, tenant.organization_id) or []
    lead_summary = await LeadService(session).linked_summary_for_event(event_id, tenant.organization_id)
    await session.commit()
    prov = _provenance_schema(row, len(obs) or 1, src_ids)
    return EventDetailSchema(
        id=event.id,
        campaign_id=event.campaign_id,
        canonical_title=event.canonical_title,
        source_url=event.source_url,
        observed_at=event.observed_at,
        description=event.description,
        organizer=event.organizer,
        region=event.region,
        starts_at=event.starts_at,
        discovery_job_id=UUID(event.discovery_job_id) if event.discovery_job_id else None,
        provenance=prov,
        observations=[
            EventSourceObservationSchema(
                id=o.id,
                source_id=o.source_id,
                source_url=o.source_url,
                observed_at=o.observed_at,
                raw_title=o.raw_title,
                discovery_job_id=UUID(o.discovery_job_id) if o.discovery_job_id else None,
            )
            for o in obs
        ],
        score=_score_detail(score) if score else None,
        score_state="ready" if score else "missing",
        audience=_audience_schema(audience),
        engagement=_engagement_schema(engagement),
        generated_content=[
            GeneratedContentSummarySchema(
                id=d.id,
                variant_index=d.variant_index,
                content_type=d.settings.content_type.value,
                platform=d.settings.platform.value,
                review_status=d.review_status.value,
                ready_for_use=is_ready_for_later_use(d.review_status),
                body_preview=d.body_text[:160] + ("…" if len(d.body_text) > 160 else ""),
                risk_flag_count=len(d.risk_flags),
                last_editor=d.metadata.last_editor if d.metadata else "system",
            )
            for d in draft_list
        ],
        leads=EventLeadLinkSchema(**lead_summary),
    )


@router.post("/events/{event_id}/engagement-plans", response_model=EventDetailSchema)
async def create_engagement_plan(
    event_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = EngagementService(session)
    result = await svc.create_or_refresh_plan(event_id, tenant.organization_id)
    if result.state == "blocked":
        raise HTTPException(status_code=409, detail=result.generation_notes[0] if result.generation_notes else "cannot create plan")
    await session.commit()
    return await get_event(event_id, tenant, session)


@router.patch("/events/{event_id}/engagement-tasks/{task_id}", response_model=EventDetailSchema)
async def patch_engagement_task(
    event_id: UUID,
    task_id: UUID,
    body: EngagementTaskUpdateSchema,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = EngagementService(session)
    try:
        updated = await svc.update_task(
            event_id,
            task_id,
            tenant.organization_id,
            status=body.status,
            assignee=body.assignee,
            notes=body.notes,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid task status transition") from None
    if updated is None:
        raise HTTPException(status_code=404, detail="task not found")
    await session.commit()
    return await get_event(event_id, tenant, session)


@router.post("/events/{event_id}/audience/refresh", response_model=EventDetailSchema)
async def refresh_audience(
    event_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    events = EventRepository(session)
    if not await events.get(event_id, tenant.organization_id):
        raise HTTPException(status_code=404, detail="event not found")
    await AudienceService(session).get_or_generate(event_id, tenant.organization_id, refresh=True)
    await session.commit()
    return await get_event(event_id, tenant, session)


@router.post("/events/{event_id}/rescore", response_model=EventDetailSchema)
async def rescore_event(
    event_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ScoringService(session)
    score = await svc.rescore_event(event_id, tenant.organization_id)
    if not score:
        raise HTTPException(status_code=404, detail="event not found or cannot score")
    await session.commit()
    return await get_event(event_id, tenant, session)