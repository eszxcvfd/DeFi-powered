"""Scoring suggestion validation (US-039)."""

from __future__ import annotations

from livelead.domain.campaigns.models import ScoringWeights
from livelead.domain.campaigns.validation import ALLOWED_WEIGHT_KEYS
from livelead.domain.scoring_suggestions.models import (
    MAX_WEIGHT_DELTA,
    ScoringSuggestionStatus,
    ScoringWeightDelta,
)


class ScoringSuggestionValidationError(ValueError):
    pass


def validate_suggestion_deltas(
    current: ScoringWeights,
    proposed_raw: dict[str, float],
) -> tuple[ScoringWeights, list[ScoringWeightDelta]]:
    """Ensure proposed weights are safe deltas from current normalized weights."""
    current_map = current.normalized().weights
    unknown = set(proposed_raw) - ALLOWED_WEIGHT_KEYS
    if unknown:
        raise ScoringSuggestionValidationError(
            f"unsupported scoring components: {sorted(unknown)}"
        )
    deltas: list[ScoringWeightDelta] = []
    for key in ALLOWED_WEIGHT_KEYS:
        cur = float(current_map.get(key, 0.0))
        prop = float(proposed_raw.get(key, cur))
        if prop < 0:
            raise ScoringSuggestionValidationError(f"{key} must be non-negative")
        if abs(prop - cur) > MAX_WEIGHT_DELTA + 1e-9:
            raise ScoringSuggestionValidationError(
                f"{key} delta exceeds safe limit ({MAX_WEIGHT_DELTA})"
            )
        if abs(prop - cur) > 1e-9:
            deltas.append(
                ScoringWeightDelta(
                    component=key,
                    current_weight=cur,
                    proposed_weight=prop,
                    rationale="",
                )
            )
    normalized = ScoringWeights(weights=dict(proposed_raw)).normalized()
    return normalized, deltas


def assert_may_decide(status: str) -> ScoringSuggestionStatus:
    try:
        parsed = ScoringSuggestionStatus(status)
    except ValueError as exc:
        raise ScoringSuggestionValidationError("invalid suggestion status") from exc
    if parsed != ScoringSuggestionStatus.PENDING_REVIEW:
        raise ScoringSuggestionValidationError(
            "only pending_review suggestions may be approved or rejected"
        )
    return parsed