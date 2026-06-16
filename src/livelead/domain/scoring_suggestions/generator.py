"""Deterministic scoring suggestions from campaign feedback signals (US-039)."""

from __future__ import annotations

from dataclasses import dataclass

from livelead.domain.campaigns.models import ScoringWeights
from livelead.domain.scoring_suggestions.models import (
    MIN_AUDIENCE_INCORRECT_FOR_SUGGESTION,
    MIN_COPILOT_NOT_HELPFUL_FOR_SUGGESTION,
    ScoringSuggestionSignal,
    ScoringSuggestionSignalKind,
    ScoringWeightDelta,
)


@dataclass(frozen=True, slots=True)
class CampaignFeedbackRollup:
    audience_incorrect: int = 0
    audience_wrong_fit: int = 0
    audience_uncertain: int = 0
    copilot_not_helpful: int = 0
    copilot_helpful: int = 0


@dataclass(frozen=True, slots=True)
class GenerationResult:
    confidence: float
    summary: str
    caution_notes: tuple[str, ...]
    assumptions: tuple[str, ...]
    signals: tuple[ScoringSuggestionSignal, ...]
    deltas: tuple[ScoringWeightDelta, ...]
    proposed_weights: dict[str, float]


def _apply_delta(weights: dict[str, float], component: str, delta: float) -> dict[str, float]:
    out = dict(weights)
    out[component] = max(0.0, out.get(component, 0.0) + delta)
    return ScoringWeights(weights=out).normalized().weights


def generate_scoring_suggestions(
    *,
    current: ScoringWeights,
    rollup: CampaignFeedbackRollup,
) -> GenerationResult | None:
    """Return a bounded suggestion set or None when signals are too sparse."""
    base = current.normalized().weights
    signals: list[ScoringSuggestionSignal] = []
    caution: list[str] = []
    assumptions = (
        "Suggestions use campaign-scoped feedback counts only.",
        "No cross-tenant or global learning is applied.",
    )

    if rollup.audience_incorrect:
        signals.append(
            ScoringSuggestionSignal(
                kind=ScoringSuggestionSignalKind.AUDIENCE_FEEDBACK,
                summary="Audience hypotheses marked incorrect",
                count=rollup.audience_incorrect,
                reason_code="incorrect",
            )
        )
    if rollup.audience_wrong_fit:
        signals.append(
            ScoringSuggestionSignal(
                kind=ScoringSuggestionSignalKind.AUDIENCE_FEEDBACK,
                summary="Incorrect feedback citing wrong audience fit",
                count=rollup.audience_wrong_fit,
                reason_code="wrong_audience_fit",
            )
        )
    if rollup.copilot_not_helpful:
        signals.append(
            ScoringSuggestionSignal(
                kind=ScoringSuggestionSignalKind.DISCOVERY_COPILOT_FEEDBACK,
                summary="Discovery copilot responses marked not helpful",
                count=rollup.copilot_not_helpful,
                reason_code="not_helpful",
            )
        )

    proposed = dict(base)
    delta_specs: list[tuple[str, float, str]] = []
    confidence = 0.0

    if rollup.audience_incorrect >= MIN_AUDIENCE_INCORRECT_FOR_SUGGESTION:
        confidence = max(confidence, 0.55)
        if rollup.audience_wrong_fit >= 1:
            delta_specs.append(
                (
                    "audience_quality",
                    -0.04,
                    "Repeated wrong-audience feedback suggests lowering audience-quality weight.",
                )
            )
            delta_specs.append(
                (
                    "topic_relevance",
                    0.04,
                    "Shift weight toward topic relevance when audience fit signals disagree.",
                )
            )
        else:
            delta_specs.append(
                (
                    "icp_match",
                    -0.03,
                    "Incorrect audience feedback may indicate ICP weight is too strong.",
                )
            )
            delta_specs.append(
                (
                    "topic_relevance",
                    0.03,
                    "Rebalance toward explicit topic signals when ICP match is disputed.",
                )
            )

    if rollup.copilot_not_helpful >= MIN_COPILOT_NOT_HELPFUL_FOR_SUGGESTION:
        confidence = max(confidence, 0.5)
        delta_specs.append(
            (
                "organizer_reputation",
                0.03,
                "Copilot usefulness issues may benefit from stronger organizer reputation cues.",
            )
        )
        delta_specs.append(
            (
                "topic_relevance",
                -0.03,
                "Reduce reliance on broad topic weight when copilot guidance is not helpful.",
            )
        )

    if rollup.audience_incorrect and rollup.copilot_helpful >= rollup.copilot_not_helpful:
        caution.append(
            "Audience disagreement coexists with helpful copilot feedback; review carefully."
        )
        confidence = min(confidence, 0.65)

    if not delta_specs:
        if signals:
            return GenerationResult(
                confidence=0.25,
                summary="Feedback recorded but not yet strong enough for weight adjustments.",
                caution_notes=tuple(
                    ["Collect more audience or copilot feedback before generating deltas."]
                ),
                assumptions=assumptions,
                signals=tuple(signals),
                deltas=(),
                proposed_weights=dict(base),
            )
        return None

    for component, delta, _rationale in delta_specs:
        proposed = _apply_delta(proposed, component, delta)

    current_map = base
    deltas: list[ScoringWeightDelta] = []
    for component, _delta, rationale in delta_specs:
        cur = float(current_map.get(component, 0.0))
        prop = float(proposed.get(component, 0.0))
        if abs(prop - cur) > 1e-9:
            deltas.append(
                ScoringWeightDelta(
                    component=component,
                    current_weight=cur,
                    proposed_weight=prop,
                    rationale=rationale,
                )
            )

    if rollup.audience_incorrect + rollup.copilot_not_helpful < 4:
        caution.append("Signal volume is still low; treat this suggestion as exploratory.")

    summary = (
        "Proposed scoring adjustments based on accumulated campaign feedback signals."
        if deltas
        else "No scoring adjustments recommended."
    )

    return GenerationResult(
        confidence=round(min(0.95, confidence), 2),
        summary=summary,
        caution_notes=tuple(caution),
        assumptions=assumptions,
        signals=tuple(signals),
        deltas=tuple(deltas),
        proposed_weights=proposed,
    )