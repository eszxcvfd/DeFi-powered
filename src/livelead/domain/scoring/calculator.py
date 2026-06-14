"""Deterministic campaign-aware event scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass

from livelead.domain.campaigns.models import Campaign, IcpCriteria
from livelead.domain.events.models import CanonicalEvent
from livelead.domain.scoring.models import (
    SCORING_VERSION,
    PriorityLevel,
    ScoreComponent,
    ScoreExplanation,
)

DEFAULT_THRESHOLDS: tuple[tuple[int, PriorityLevel], ...] = (
    (85, PriorityLevel.VERY_HIGH),
    (70, PriorityLevel.HIGH),
    (50, PriorityLevel.WATCH),
    (30, PriorityLevel.REFERENCE_ONLY),
    (0, PriorityLevel.POOR_FIT),
)


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 2)))


def priority_from_score(total: float) -> PriorityLevel:
    t = clamp_score(total)
    for threshold, level in DEFAULT_THRESHOLDS:
        if t >= threshold:
            return level
    return PriorityLevel.POOR_FIT


def _tokenize(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[a-z0-9]{3,}", text.lower())}


def _keyword_overlap(haystack: str, keywords: tuple[str, ...]) -> float:
    if not keywords:
        return 50.0
    tokens = _tokenize(haystack)
    keys = {k.lower().strip() for k in keywords if k.strip()}
    if not keys:
        return 50.0
    hits = sum(1 for k in keys if k in tokens or any(k in t for t in tokens))
    return clamp_score(40.0 + (hits / len(keys)) * 60.0)


@dataclass(frozen=True, slots=True)
class ScoreResult:
    total_score: float
    priority_level: PriorityLevel
    scoring_version: str
    weights_snapshot: dict[str, float]
    components: tuple[ScoreComponent, ...]
    explanation: ScoreExplanation


def _component_topic(event: CanonicalEvent, campaign: Campaign) -> ScoreComponent:
    text = f"{event.canonical_title} {event.description}"
    pos = campaign.positive_keywords + campaign.icp.positive_keywords
    raw = _keyword_overlap(text, pos)
    missing: list[str] = []
    if not pos:
        missing.append("campaign_positive_keywords")
    excl = campaign.exclude_keywords + campaign.icp.excluded_keywords
    reducers = 0.0
    for ex in excl:
        if ex and ex.lower() in text.lower():
            reducers += 25.0
    raw = clamp_score(raw - reducers)
    return ScoreComponent(
        key="topic_relevance",
        raw_value=raw,
        weighted_contribution=0.0,
        evidence=f"keyword overlap vs {len(pos)} positive terms",
        missing_data=missing,
    )


def _component_icp(event: CanonicalEvent, icp: IcpCriteria) -> ScoreComponent:
    text = f"{event.canonical_title} {event.description} {event.organizer} {event.region}"
    missing: list[str] = []
    score = 50.0
    if icp.industry:
        if icp.industry.lower() in text.lower():
            score += 25.0
        else:
            score -= 10.0
    else:
        missing.append("icp.industry")
    if icp.country_or_region and event.region:
        if icp.country_or_region.lower() in event.region.lower():
            score += 15.0
    elif not event.region:
        missing.append("event.region")
    raw = clamp_score(score)
    return ScoreComponent(
        key="icp_match",
        raw_value=raw,
        weighted_contribution=0.0,
        evidence="ICP industry/region heuristic",
        missing_data=missing,
    )


def _heuristic_component(
    key: str, event: CanonicalEvent, base: float, field_name: str
) -> ScoreComponent:
    missing: list[str] = []
    raw = base
    if key == "organizer_reputation":
        if event.organizer:
            raw = 65.0
        else:
            raw = 40.0
            missing.append("organizer")
    elif key == "speaker_relevance":
        raw = 45.0
        missing.append("speakers_not_modeled")
    elif key == "audience_quality":
        raw = 50.0
        missing.append("audience_signals_deferred")
    elif key == "engagement_accessibility":
        fmt = event.metadata_json.get("format", "")
        raw = 70.0 if "webinar" in fmt.lower() or "virtual" in event.description.lower() else 55.0
    elif key == "replay_availability":
        raw = 60.0 if "replay" in event.description.lower() else 45.0
        if "replay" not in event.description.lower():
            missing.append("replay_signal")
    elif key == "geographic_fit":
        if event.region:
            raw = 70.0
        else:
            raw = 50.0
            missing.append(field_name)
    elif key == "timing_fit":
        raw = 60.0 if event.starts_at else 48.0
        if not event.starts_at:
            missing.append("starts_at")
    return ScoreComponent(
        key=key,
        raw_value=clamp_score(raw),
        weighted_contribution=0.0,
        evidence=f"deterministic heuristic ({key})",
        missing_data=missing,
    )


def calculate_event_score(event: CanonicalEvent, campaign: Campaign) -> ScoreResult:
    weights = campaign.scoring_weights.normalized()
    wmap = weights.weights

    built: list[ScoreComponent] = [
        _component_topic(event, campaign),
        _component_icp(event, campaign.icp),
        _heuristic_component("organizer_reputation", event, 50.0, "organizer"),
        _heuristic_component("speaker_relevance", event, 45.0, "speakers"),
        _heuristic_component("audience_quality", event, 50.0, "audience"),
        _heuristic_component("engagement_accessibility", event, 55.0, "format"),
        _heuristic_component("replay_availability", event, 45.0, "replay"),
        _heuristic_component("geographic_fit", event, 50.0, "region"),
        _heuristic_component("timing_fit", event, 48.0, "starts_at"),
    ]

    total = 0.0
    final_components: list[ScoreComponent] = []
    all_missing: list[str] = []
    reducers: list[str] = []

    for comp in built:
        w = wmap.get(comp.key, 0.0)
        contrib = comp.raw_value * w
        total += contrib
        all_missing.extend(comp.missing_data)
        final_components.append(
            ScoreComponent(
                key=comp.key,
                raw_value=comp.raw_value,
                weighted_contribution=round(contrib, 2),
                evidence=comp.evidence,
                missing_data=list(comp.missing_data),
            )
        )

    for ex in campaign.exclude_keywords:
        if ex and ex.lower() in event.canonical_title.lower():
            reducers.append(f"exclude_keyword:{ex}")

    total_score = clamp_score(total)
    if reducers:
        total_score = clamp_score(total_score - min(15.0, 5.0 * len(reducers)))

    explanation = ScoreExplanation(
        components=tuple(final_components),
        missing_fields=tuple(sorted(set(all_missing))),
        score_reducers=tuple(reducers),
    )

    return ScoreResult(
        total_score=total_score,
        priority_level=priority_from_score(total_score),
        scoring_version=SCORING_VERSION,
        weights_snapshot=dict(wmap),
        components=tuple(final_components),
        explanation=explanation,
    )
