"""Deterministic audience hypothesis generation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from livelead.domain.audience.models import (
    AUDIENCE_STRATEGY_VERSION,
    AudienceAnalysisState,
    AudienceEvidenceItem,
    AudienceHypothesis,
    EvidenceKind,
    FitType,
)
from livelead.domain.audience.safety import contains_sensitive_inference, sanitize_or_block
from livelead.domain.campaigns.models import Campaign
from livelead.domain.events.models import CanonicalEvent, EventSourceObservation

logger = logging.getLogger("livelead.audience")


@dataclass(frozen=True, slots=True)
class GenerationContext:
    event: CanonicalEvent
    campaign: Campaign
    observations: tuple[EventSourceObservation, ...]


def _text_blob(ctx: GenerationContext) -> str:
    e = ctx.event
    parts = [e.canonical_title, e.description, e.organizer, e.region]
    for o in ctx.observations:
        parts.append(o.raw_title)
    return " ".join(p for p in parts if p).lower()


def _confidence_from_richness(blob: str, evidence_count: int) -> float:
    score = 0.35
    if len(blob) > 80:
        score += 0.15
    if "b2b" in blob or "saas" in blob or "enterprise" in blob:
        score += 0.15
    if "partner" in blob or "payments" in blob or "fintech" in blob:
        score += 0.1
    score += min(0.25, evidence_count * 0.08)
    return round(min(0.95, max(0.2, score)), 2)


def _mk_hypothesis(
    ctx: GenerationContext,
    *,
    segment_name: str,
    fit_type: FitType,
    reason: str,
    evidence: list[AudienceEvidenceItem],
) -> AudienceHypothesis | None:
    seg = sanitize_or_block(segment_name)
    rsn = sanitize_or_block(reason)
    if not seg or not rsn:
        logger.info("audience_hypothesis_blocked_sensitive event_id=%s", ctx.event.id)
        return None
    if contains_sensitive_inference(" ".join(e.detail for e in evidence)):
        return None
    conf = _confidence_from_richness(_text_blob(ctx), len(evidence))
    return AudienceHypothesis(
        id=uuid4(),
        event_id=ctx.event.id,
        segment_name=seg,
        fit_type=fit_type,
        reason=rsn,
        confidence=conf,
        generated_by="deterministic_heuristic",
        model_version=AUDIENCE_STRATEGY_VERSION,
        evidence=tuple(evidence),
        created_at=datetime.now(UTC),
    )


def generate_audience_analysis(ctx: GenerationContext) -> AudienceAnalysisState:
    blob = _text_blob(ctx)
    notes: list[str] = []

    if len(blob.strip()) < 20:
        return AudienceAnalysisState(
            state="empty",
            hypotheses=(),
            generation_notes=("Insufficient event context for reliable audience segments.",),
        )

    icp = ctx.campaign.icp
    industry = (icp.industry or ctx.campaign.target_industry or "target").strip()
    hypotheses: list[AudienceHypothesis] = []

    ev_title = AudienceEvidenceItem(
        cue="event_title",
        kind=EvidenceKind.OBSERVED,
        detail=ctx.event.canonical_title,
        source_field="canonical_title",
    )
    if "webinar" in blob or "summit" in blob or "meetup" in blob:
        h = _mk_hypothesis(
            ctx,
            segment_name=f"{industry} practitioners seeking live education",
            fit_type=FitType.CUSTOMER,
            reason=(
                f"Event format and topic cues suggest attendees interested in {industry} "
                "education and vendor evaluation."
            ),
            evidence=[
                ev_title,
                AudienceEvidenceItem(
                    cue="format_signal",
                    kind=EvidenceKind.INFERRED,
                    detail="Title/description mention webinar, summit, or meetup format.",
                    source_field="description",
                ),
            ],
        )
        if h:
            hypotheses.append(h)

    if icp.industry and icp.industry.lower() in blob:
        h = _mk_hypothesis(
            ctx,
            segment_name=f"ICP-aligned {icp.industry} buyers",
            fit_type=FitType.CUSTOMER,
            reason="Campaign ICP industry appears in observable event text.",
            evidence=[
                ev_title,
                AudienceEvidenceItem(
                    cue="icp_industry_match",
                    kind=EvidenceKind.OBSERVED,
                    detail=f"ICP industry '{icp.industry}' matches event-visible cues.",
                    source_field="icp",
                ),
            ],
        )
        if h:
            hypotheses.append(h)

    if "partner" in blob or "partnership" in blob or ctx.campaign.product_or_service_focus:
        focus = ctx.campaign.product_or_service_focus or "integration"
        h = _mk_hypothesis(
            ctx,
            segment_name="Partnership and ecosystem leaders",
            fit_type=FitType.PARTNER,
            reason=f"Event or campaign focus suggests partner-facing audiences around {focus}.",
            evidence=[
                AudienceEvidenceItem(
                    cue="partner_signal",
                    kind=EvidenceKind.INFERRED,
                    detail="Partnership language or product focus in campaign/event context.",
                    source_field="product_or_service_focus",
                ),
            ],
        )
        if h:
            hypotheses.append(h)

    if ctx.event.region or icp.country_or_region:
        region = ctx.event.region or icp.country_or_region
        h = _mk_hypothesis(
            ctx,
            segment_name=f"Regional referral network ({region})",
            fit_type=FitType.REFERRAL,
            reason="Geographic alignment supports referral-style introductions in this region.",
            evidence=[
                AudienceEvidenceItem(
                    cue="region",
                    kind=EvidenceKind.OBSERVED if ctx.event.region else EvidenceKind.INFERRED,
                    detail=f"Region cue: {region}",
                    source_field="region",
                ),
            ],
        )
        if h:
            hypotheses.append(h)

    if not hypotheses:
        notes.append("No segment rules matched; safe empty result.")
        return AudienceAnalysisState(state="empty", hypotheses=(), generation_notes=tuple(notes))

    # Deduplicate by segment_name
    seen: set[str] = set()
    unique: list[AudienceHypothesis] = []
    for h in hypotheses:
        key = h.segment_name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(h)

    return AudienceAnalysisState(
        state="ready",
        hypotheses=tuple(unique),
        generation_notes=tuple(notes),
    )