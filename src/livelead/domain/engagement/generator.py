"""Deterministic engagement plan generation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from livelead.domain.audience.models import AudienceHypothesis
from livelead.domain.campaigns.models import Campaign
from livelead.domain.engagement.models import (
    ENGAGEMENT_STRATEGY_VERSION,
    EngagementPhase,
    EngagementPlan,
    EngagementPlanState,
    EngagementTask,
    EngagementTaskStatus,
)
from livelead.domain.engagement.safety import filter_safe_tasks, task_text_is_unsafe
from livelead.domain.events.models import CanonicalEvent
from livelead.domain.scoring.models import EventScore

logger = logging.getLogger("livelead.engagement")


@dataclass(frozen=True, slots=True)
class PlanGenerationContext:
    event: CanonicalEvent
    campaign: Campaign
    score: EventScore | None
    hypotheses: tuple[AudienceHypothesis, ...]


def _template_tasks(ctx: PlanGenerationContext) -> list[tuple[EngagementPhase, str, str]]:
    title = ctx.event.canonical_title
    focus = ctx.campaign.product_or_service_focus or ctx.campaign.target_industry or "your offer"
    region = ctx.event.region or (
        ctx.campaign.market_regions[0] if ctx.campaign.market_regions else ""
    )
    top_segment = ctx.hypotheses[0].segment_name if ctx.hypotheses else "target attendees"

    tasks: list[tuple[EngagementPhase, str, str]] = [
        (
            EngagementPhase.PRE_EVENT,
            "Confirm event fit and internal owner",
            f"Review score and audience fit for '{title}' and assign a single owner before outreach.",
        ),
        (
            EngagementPhase.PRE_EVENT,
            "Prepare value-first talking points",
            f"Draft 3 helpful talking points about {focus} tailored to {top_segment}; avoid unsolicited bulk outreach.",
        ),
        (
            EngagementPhase.PRE_EVENT,
            "Research organizer and agenda",
            f"Validate agenda, speakers, and registration path for {title} in {region or 'the listed region'}.",
        ),
        (
            EngagementPhase.LIVE_EVENT,
            "Join with a clear learning goal",
            "Attend sessions relevant to campaign ICP; capture public takeaways only (no attendee scraping).",
        ),
        (
            EngagementPhase.LIVE_EVENT,
            "Engage in Q&A or chat thoughtfully",
            "Ask one substantive question or share one useful resource when appropriate.",
        ),
        (
            EngagementPhase.POST_EVENT,
            "Send personalized follow-up",
            f"Follow up with contacts who opted in; reference {focus} value, not mass messaging.",
        ),
        (
            EngagementPhase.POST_EVENT,
            "Log outcomes in LiveLead",
            "Record notes and next steps inside LiveLead; content studio and lead pipeline remain separate.",
        ),
    ]
    if ctx.score and ctx.score.total_score >= 70:
        tasks.insert(
            2,
            (
                EngagementPhase.PRE_EVENT,
                "Align stakeholders on priority",
                f"High-priority event (score {ctx.score.total_score:.0f}); confirm calendar hold before the event date.",
            ),
        )
    return tasks


def generate_engagement_plan(ctx: PlanGenerationContext) -> EngagementPlanState:
    if not ctx.event.canonical_title.strip():
        return EngagementPlanState(
            state="blocked",
            generation_notes=("Event title missing; cannot build a plan.",),
        )

    raw = _template_tasks(ctx)
    safe = filter_safe_tasks(raw)
    if not safe:
        return EngagementPlanState(
            state="blocked",
            generation_notes=("No safe tasks could be generated for this context.",),
        )

    now = datetime.now(UTC)
    plan_id = uuid4()
    event_id = ctx.event.id
    campaign_id = ctx.event.campaign_id
    starts = ctx.event.starts_at

    built: list[EngagementTask] = []
    for phase, title, rationale in safe:
        if task_text_is_unsafe(title, rationale):
            logger.info("engagement_task_blocked event_id=%s title=%s", event_id, title)
            continue
        deadline: datetime | None = None
        if starts:
            if phase == EngagementPhase.PRE_EVENT:
                deadline = starts - timedelta(days=3)
            elif phase == EngagementPhase.LIVE_EVENT:
                deadline = starts
            else:
                deadline = starts + timedelta(days=5)
        built.append(
            EngagementTask(
                id=uuid4(),
                plan_id=plan_id,
                event_id=event_id,
                phase=phase,
                title=title,
                rationale=rationale,
                status=EngagementTaskStatus.TODO,
                assignee="",
                deadline=deadline,
                notes="",
                created_at=now,
                updated_at=now,
            )
        )

    if not built:
        return EngagementPlanState(
            state="blocked", generation_notes=("All suggested tasks were filtered by guardrails.",)
        )

    plan = EngagementPlan(
        id=plan_id,
        event_id=event_id,
        campaign_id=campaign_id,
        strategy_version=ENGAGEMENT_STRATEGY_VERSION,
        generation_notes=(),
        created_at=now,
        updated_at=now,
    )
    return EngagementPlanState(state="ready", plan=plan, tasks=tuple(built))
