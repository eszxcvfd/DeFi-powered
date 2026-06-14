"""Orchestrate draft generation with metadata and risk flags."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from livelead.domain.audience.models import AudienceAnalysisState
from livelead.domain.campaigns.models import Campaign
from livelead.domain.content.context import build_context_preview
from livelead.domain.content.models import (
    CONTENT_TEMPLATE_VERSION,
    ContentContextPreview,
    ContentGenerationSettings,
    ContentReviewStatus,
    GeneratedContentDraft,
    GenerationMetadata,
)
from livelead.domain.content.ports import ContentProviderPort
from livelead.domain.content.risk import evaluate_draft_risks
from livelead.domain.content.validation import validate_settings
from livelead.domain.engagement.models import EngagementPlanState
from livelead.domain.events.models import CanonicalEvent
from livelead.domain.scoring.models import EventScore


def generate_drafts(
    *,
    event_id: UUID,
    campaign_id: UUID,
    engagement_plan_id: UUID | None,
    event: CanonicalEvent,
    campaign: Campaign,
    score: EventScore | None,
    audience: AudienceAnalysisState,
    plan: EngagementPlanState,
    settings: ContentGenerationSettings,
    provider: ContentProviderPort,
) -> tuple[ContentContextPreview, list[GeneratedContentDraft], list[str]]:
    errors = validate_settings(settings)
    preview = build_context_preview(event, campaign, score, audience, plan)
    if errors:
        return preview, [], errors

    raw_variants = provider.generate_variants(preview, settings)
    now = datetime.now(UTC)
    meta_base = GenerationMetadata(
        provider=provider.provider_id,
        model=provider.model_id,
        prompt_template_version=CONTENT_TEMPLATE_VERSION,
        input_context_summary=f"{preview.event_title}|{preview.campaign_focus}|tasks={preview.plan_task_count}",
        generated_at=now,
        last_editor="system",
    )

    drafts: list[GeneratedContentDraft] = []
    bodies: list[str] = []
    for idx, body_text in enumerate(raw_variants):
        flags = evaluate_draft_risks(
            body_text,
            event_title=preview.event_title,
            cta=settings.cta,
            prior_bodies=tuple(bodies),
        )
        bodies.append(body_text)
        drafts.append(
            GeneratedContentDraft(
                id=uuid4(),
                event_id=event_id,
                campaign_id=campaign_id,
                engagement_plan_id=engagement_plan_id,
                variant_index=idx,
                review_status=ContentReviewStatus.DRAFT,
                settings=settings,
                body_text=body_text,
                risk_flags=flags,
                metadata=meta_base,
                created_at=now,
                updated_at=now,
            )
        )
    return preview, drafts, []
