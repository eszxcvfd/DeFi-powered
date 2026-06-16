"""Governed scoring suggestion domain types (US-039)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ScoringSuggestionStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ScoringSuggestionSignalKind(StrEnum):
    AUDIENCE_FEEDBACK = "audience_feedback"
    DISCOVERY_COPILOT_FEEDBACK = "discovery_copilot_feedback"


MAX_WEIGHT_DELTA = 0.05
MIN_AUDIENCE_INCORRECT_FOR_SUGGESTION = 2
MIN_COPILOT_NOT_HELPFUL_FOR_SUGGESTION = 2


@dataclass(frozen=True, slots=True)
class ScoringSuggestionSignal:
    kind: ScoringSuggestionSignalKind
    summary: str
    count: int
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class ScoringWeightDelta:
    component: str
    current_weight: float
    proposed_weight: float
    rationale: str

    @property
    def delta(self) -> float:
        return self.proposed_weight - self.current_weight


@dataclass(frozen=True, slots=True)
class ScoringSuggestionSet:
    id: UUID
    organization_id: UUID
    campaign_id: UUID
    status: ScoringSuggestionStatus
    confidence: float
    summary: str
    caution_notes: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    signals: tuple[ScoringSuggestionSignal, ...] = ()
    deltas: tuple[ScoringWeightDelta, ...] = ()
    current_weights: dict[str, float] = field(default_factory=dict)
    proposed_weights: dict[str, float] = field(default_factory=dict)
    generated_by: str = ""
    decided_by: str | None = None
    decided_at: datetime | None = None
    review_note: str | None = None
    weight_snapshot_id: UUID | None = None
    created_at: datetime | None = None