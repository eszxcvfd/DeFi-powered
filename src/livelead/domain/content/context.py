"""Assemble generation context from event intelligence slices."""

from livelead.domain.audience.models import AudienceAnalysisState
from livelead.domain.campaigns.models import Campaign
from livelead.domain.content.models import ContentContextPreview
from livelead.domain.engagement.models import EngagementPlanState
from livelead.domain.events.models import CanonicalEvent
from livelead.domain.scoring.models import EventScore


def build_context_preview(
    event: CanonicalEvent,
    campaign: Campaign,
    score: EventScore | None,
    audience: AudienceAnalysisState,
    plan: EngagementPlanState,
) -> ContentContextPreview:
    aud = ""
    if audience.hypotheses:
        top = audience.hypotheses[0]
        aud = f"{top.segment_name} ({top.fit_type.value}, {top.confidence:.0%})"
    score_s = "not scored"
    if score:
        score_s = f"{score.total_score:.1f} — {score.priority_level.value}"
    tasks = len(plan.tasks) if plan.state == "ready" else 0
    notes: list[str] = []
    if plan.state != "ready":
        notes.append("Engagement plan recommended before generating drafts.")
    return ContentContextPreview(
        event_title=event.canonical_title,
        event_description=event.description or event.organizer,
        campaign_focus=campaign.product_or_service_focus or campaign.target_industry,
        score_summary=score_s,
        audience_summary=aud or (audience.generation_notes[0] if audience.generation_notes else "—"),
        plan_task_count=tasks,
        notes=tuple(notes),
    )