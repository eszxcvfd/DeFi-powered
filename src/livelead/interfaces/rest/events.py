from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.ai_feedback.service import AiFeedbackService, resolve_feedback_actor_key
from livelead.application.audience.service import AudienceService
from livelead.application.browser.service import BrowserSessionService
from livelead.application.content.service import ContentService
from livelead.application.engagement.service import EngagementService
from livelead.application.event_overrides import EventOverrideService
from livelead.application.event_watchlist import EventWatchlistService
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
from livelead.domain.ai_feedback.models import AiFeedbackTargetType
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
    FieldProvenanceSchema,
    GeneratedContentSummarySchema,
    ScoreComponentSchema,
    ViewerFeedbackSchema,
    WatchStateSchema,
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


def _feedback_schema(proj) -> ViewerFeedbackSchema | None:
    if proj is None:
        return None
    return ViewerFeedbackSchema(
        state=proj.state,
        reason_code=proj.reason_code,
        note=proj.note,
        updated_at=proj.updated_at,
    )


def _audience_schema(analysis, feedback_by_hypothesis: dict | None = None) -> AudienceAnalysisSchema:
    fb = feedback_by_hypothesis or {}
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
                viewer_feedback=_feedback_schema(fb.get(h.id)),
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


@router.get("/events", response_model=list[EventListItemSchema])
async def list_organization_events(
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    include_score: bool = Query(default=False),
    watched: bool | None = Query(default=None),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    events = EventRepository(session)
    rows = await events.list_for_organization(
        tenant.organization_id,
        q=q,
        limit=limit,
    )
    counts = await events.observation_counts([e.id for e in rows])
    campaigns = CampaignRepository(session)
    name_by_id = {
        c.id: c.name for c in await campaigns.list_for_organization(tenant.organization_id)
    }
    score_map: dict[UUID, object] = {}
    if include_score and rows:
        scores = EventScoreRepository(session)
        by_campaign: dict[UUID, list[UUID]] = {}
        for e in rows:
            by_campaign.setdefault(e.campaign_id, []).append(e.id)
        for cid, eids in by_campaign.items():
            score_map.update(await scores.get_current_for_events(eids, cid))
    source_counts: dict[UUID, int] = {}
    for e in rows:
        src_ids = await events.distinct_source_ids(e.id)
        source_counts[e.id] = len(src_ids) or 1
    watch_states = await _project_watch_states(
        session, tenant, [e.id for e in rows]
    )
    await session.commit()
    out: list[EventListItemSchema] = []
    for e in rows:
        watch_state = watch_states.get(e.id)
        is_watched = bool(watch_state and watch_state.is_watched)
        if watched is True and not is_watched:
            continue
        if watched is False and is_watched:
            continue
        obs_n = counts.get(e.id, 1)
        out.append(
            EventListItemSchema(
                id=e.id,
                campaign_id=e.campaign_id,
                campaign_name=name_by_id.get(e.campaign_id, ""),
                canonical_title=e.canonical_title,
                source_url=e.source_url,
                observed_at=e.observed_at,
                region=e.region,
                confidence_summary=e.confidence_summary,
                observation_count=obs_n,
                source_count=source_counts.get(e.id, 1),
                discovery_job_id=UUID(e.discovery_job_id) if e.discovery_job_id else None,
                score=_score_summary(score_map.get(e.id)) if include_score else None,
                watch=watch_state,
                deferred={"scoring": "available" if include_score else "omitted"},
            )
        )
    return out


@router.get("/campaigns/{campaign_id}/events", response_model=list[EventListItemSchema])
async def list_campaign_events(
    campaign_id: UUID,
    discovery_job_id: UUID | None = Query(default=None),
    source_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None, max_length=200),
    include_score: bool = Query(default=True),
    watched: bool | None = Query(default=None),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    campaigns = CampaignRepository(session)
    camp = await campaigns.get(campaign_id, tenant.organization_id)
    if not camp:
        raise HTTPException(status_code=404, detail="campaign not found")
    campaign_name = camp.name
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
    watch_states = await _project_watch_states(
        session, tenant, [e.id for e in rows]
    )
    await session.commit()
    out: list[EventListItemSchema] = []
    for e in rows:
        watch_state = watch_states.get(e.id)
        is_watched = bool(watch_state and watch_state.is_watched)
        if watched is True and not is_watched:
            continue
        if watched is False and is_watched:
            continue
        obs_n = counts.get(e.id, 1)
        item = EventListItemSchema(
            id=e.id,
            campaign_id=e.campaign_id,
            campaign_name=campaign_name,
            canonical_title=e.canonical_title,
            source_url=e.source_url,
            observed_at=e.observed_at,
            region=e.region,
            confidence_summary=e.confidence_summary,
            observation_count=obs_n,
            source_count=source_counts.get(e.id, 1),
            discovery_job_id=UUID(e.discovery_job_id) if e.discovery_job_id else None,
            score=_score_summary(score_map.get(e.id)) if include_score else None,
            watch=watch_state,
            deferred={"scoring": "available" if include_score else "omitted"},
        )
        out.append(item)
    return out


@router.get("/events/{event_id}/browser-launch-sources")
async def list_event_browser_launch_sources(
    event_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = BrowserSessionService(session)
    try:
        options = await svc.list_launch_sources_for_event(
            tenant.organization_id, event_id, actor=tenant.actor_role
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [
        {
            "source_id": str(o.source_id),
            "name": o.name,
            "domain": o.domain,
            "automation_engine": o.automation_engine,
            "engine": o.engine,
            "runnable": o.runnable,
            "denied_reasons": list(o.denied_reasons),
        }
        for o in options
    ]


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
    actor_key = resolve_feedback_actor_key(actor_id=tenant.actor_id, actor_role=tenant.actor_role)
    hyp_ids = [h.id for h in audience.hypotheses]
    feedback_map = await AiFeedbackService(session).project_for_viewer(
        tenant.organization_id,
        actor_key,
        AiFeedbackTargetType.AUDIENCE_HYPOTHESIS,
        hyp_ids,
    )
    engagement = await EngagementService(session).get_plan_state(event_id, tenant.organization_id)
    draft_list = await ContentService(session).list_drafts(event_id, tenant.organization_id) or []
    lead_summary = await LeadService(session).linked_summary_for_event(
        event_id, tenant.organization_id
    )
    watch_state = await _event_watch_state(session, tenant, event_id)
    overrides = await _event_override_provenance(session, tenant, event_id)
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
        audience=_audience_schema(audience, feedback_map),
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
        watch=watch_state,
        overrides=overrides,
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
        raise HTTPException(
            status_code=409,
            detail=result.generation_notes[0] if result.generation_notes else "cannot create plan",
        )
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


async def _resolve_current_user(tenant: TenantContext) -> tuple[UUID, str] | None:
    """Return (user_id, role) for the current user, or ``None`` if dev-header mode.

    The watchlist is user-scoped. Dev-header mode does not carry a
    user identity, so the list/detail projections return a neutral
    "no watch" state instead of inventing one.
    """

    if not tenant.is_authenticated() or not tenant.actor_id or tenant.role is None:
        return None
    try:
        return UUID(tenant.actor_id), tenant.role.value
    except (TypeError, ValueError):
        return None


async def _project_watch_states(
    session: AsyncSession,
    tenant: TenantContext,
    event_ids: list[UUID],
) -> dict[UUID, WatchStateSchema]:
    identity = await _resolve_current_user(tenant)
    if identity is None or not event_ids:
        return {}
    user_id, _role = identity
    svc = EventWatchlistService(session)
    states = await svc.project_state(tenant.organization_id, user_id, event_ids)
    return {
        event_id: WatchStateSchema.from_domain(state)
        for event_id, state in states.items()
    }


async def _event_watch_state(
    session: AsyncSession,
    tenant: TenantContext,
    event_id: UUID,
) -> WatchStateSchema:
    identity = await _resolve_current_user(tenant)
    if identity is None:
        return WatchStateSchema.unwatched_for(event_id)
    user_id, _role = identity
    svc = EventWatchlistService(session)
    state = await svc.get_state(tenant.organization_id, user_id, event_id)
    return WatchStateSchema.from_domain(state)


async def _event_override_provenance(
    session: AsyncSession,
    tenant: TenantContext,
    event_id: UUID,
) -> list[FieldProvenanceSchema]:
    """Return the per-field provenance for one canonical event.

    The projection is the same regardless of the caller's role so
    every reviewer can see the override badge.
    """

    svc = EventOverrideService(session)
    provenance = await svc.project_field_provenance(tenant.organization_id, event_id)
    return [FieldProvenanceSchema.from_domain(p) for p in provenance]
