"""Audience hypotheses from observable event + source evidence only."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from livelead.domain.audience.evidence import (
    confidence_from_observed_cues,
    icp_industry_in_event_text,
    is_likely_fixture_event_title,
    region_observed_on_event,
    snapshot_from_event,
    text_has_b2b_signal,
    text_has_partner_signal,
    text_has_referral_signal,
    title_has_format_signal,
)
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


def _mk_hypothesis(
    ctx: GenerationContext,
    *,
    segment_name: str,
    fit_type: FitType,
    reason: str,
    evidence: list[AudienceEvidenceItem],
    confidence: float,
) -> AudienceHypothesis | None:
    seg = sanitize_or_block(segment_name)
    rsn = sanitize_or_block(reason)
    if not seg or not rsn:
        logger.info("audience_hypothesis_blocked_sensitive event_id=%s", ctx.event.id)
        return None
    if contains_sensitive_inference(" ".join(e.detail for e in evidence)):
        return None
    if not any(e.kind == EvidenceKind.OBSERVED for e in evidence):
        return None
    return AudienceHypothesis(
        id=uuid4(),
        event_id=ctx.event.id,
        segment_name=seg,
        fit_type=fit_type,
        reason=rsn,
        confidence=confidence,
        generated_by="evidence_rules_v2",
        model_version=AUDIENCE_STRATEGY_VERSION,
        evidence=tuple(evidence),
        created_at=datetime.now(UTC),
    )


def generate_audience_analysis(ctx: GenerationContext) -> AudienceAnalysisState:
    snap = snapshot_from_event(ctx.event, ctx.observations)
    blob = snap.text.lower()
    notes: list[str] = []

    if len(snap.text.strip()) < 24:
        return AudienceAnalysisState(
            state="empty",
            hypotheses=(),
            generation_notes=("Insufficient observable event text for audience segments.",),
        )

    if is_likely_fixture_event_title(snap.title):
        return AudienceAnalysisState(
            state="empty",
            hypotheses=(),
            generation_notes=(
                "Event title matches discovery fixture templates; refresh discovery with real feeds before audience analysis.",
            ),
        )

    icp = ctx.campaign.icp
    industry = (icp.industry or ctx.campaign.target_industry or "").strip()
    hypotheses: list[AudienceHypothesis] = []

    ev_title = AudienceEvidenceItem(
        cue="event_title",
        kind=EvidenceKind.OBSERVED,
        detail=ctx.event.canonical_title,
        source_field="canonical_title",
    )

    observed_cues = 0
    if snap.has_description:
        observed_cues += 1
    if snap.has_organizer:
        observed_cues += 1
    if snap.observation_count:
        observed_cues += 1

    conf_base = confidence_from_observed_cues(observed_cues=observed_cues, text_len=len(snap.text))

    if title_has_format_signal(snap.text):
        topic = industry or "this topic"
        detail_fmt = _format_evidence_detail(snap.text)
        h = _mk_hypothesis(
            ctx,
            segment_name=f"Attendees interested in {topic} (live event format)",
            fit_type=FitType.CUSTOMER,
            reason=(
                f"Observable title or description mentions a live event format; "
                f"likely attracts practitioners evaluating {topic}."
            ),
            evidence=[
                ev_title,
                AudienceEvidenceItem(
                    cue="format_in_source_text",
                    kind=EvidenceKind.OBSERVED,
                    detail=detail_fmt,
                    source_field="canonical_title",
                ),
            ],
            confidence=conf_base,
        )
        if h:
            hypotheses.append(h)

    if industry and icp_industry_in_event_text(industry, snap.text):
        h = _mk_hypothesis(
            ctx,
            segment_name=f"{industry} buyers (ICP term in event text)",
            fit_type=FitType.CUSTOMER,
            reason=f"The term '{industry}' appears in observable event or source titles, aligning with campaign ICP.",
            evidence=[
                ev_title,
                AudienceEvidenceItem(
                    cue="icp_term_in_event",
                    kind=EvidenceKind.OBSERVED,
                    detail=f"Matched ICP industry '{industry}' in event-visible text.",
                    source_field="icp",
                ),
            ],
            confidence=conf_base,
        )
        if h:
            hypotheses.append(h)

    if text_has_partner_signal(snap.text):
        h = _mk_hypothesis(
            ctx,
            segment_name="Partner / ecosystem audience (from event wording)",
            fit_type=FitType.PARTNER,
            reason="Partnership, integration, or ecosystem language appears in the event title or description.",
            evidence=[
                ev_title,
                AudienceEvidenceItem(
                    cue="partner_wording",
                    kind=EvidenceKind.OBSERVED,
                    detail=_partner_evidence_detail(snap.text),
                    source_field="description",
                ),
            ],
            confidence=conf_base,
        )
        if h:
            hypotheses.append(h)
    elif text_has_b2b_signal(snap.text) and snap.has_description:
        h = _mk_hypothesis(
            ctx,
            segment_name="B2B product and platform stakeholders",
            fit_type=FitType.PARTNER,
            reason="B2B/SaaS/platform cues in observable event text suggest vendor or integration conversations.",
            evidence=[
                ev_title,
                AudienceEvidenceItem(
                    cue="b2b_wording",
                    kind=EvidenceKind.OBSERVED,
                    detail="Event text includes B2B, SaaS, enterprise, API, or developer cues.",
                    source_field="description",
                ),
            ],
            confidence=max(0.22, conf_base - 0.08),
        )
        if h:
            hypotheses.append(h)

    region = region_observed_on_event(ctx.event)
    if region and (text_has_referral_signal(snap.text) or "network" in blob):
        h = _mk_hypothesis(
            ctx,
            segment_name=f"Regional community ({region})",
            fit_type=FitType.REFERRAL,
            reason="Event lists a region and networking/referral-style wording in source-visible text.",
            evidence=[
                AudienceEvidenceItem(
                    cue="region_on_event",
                    kind=EvidenceKind.OBSERVED,
                    detail=f"Event region: {region}",
                    source_field="region",
                ),
                AudienceEvidenceItem(
                    cue="network_wording",
                    kind=EvidenceKind.OBSERVED,
                    detail="Referral or networking terms appear in event-visible text.",
                    source_field="description",
                ),
            ],
            confidence=conf_base,
        )
        if h:
            hypotheses.append(h)

    if not hypotheses:
        notes.append(
            "No audience segment matched observable event text. Add description/organizer from discovery or link more source evidence."
        )
        return AudienceAnalysisState(state="empty", hypotheses=(), generation_notes=tuple(notes))

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


def _format_evidence_detail(text: str) -> str:
    lower = text.lower()
    for term in ("webinar", "summit", "meetup", "conference", "workshop", "roundtable"):
        if term in lower:
            return f"Source text mentions '{term}'."
    return "Source text mentions a live event format."


def _partner_evidence_detail(text: str) -> str:
    lower = text.lower()
    for term in ("partnership", "partner", "ecosystem", "integration", "sponsor"):
        if term in lower:
            return f"Source text mentions '{term}'."
    return "Partnership-related wording in source-visible text."
