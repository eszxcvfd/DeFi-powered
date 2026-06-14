"""Scoring domain types."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

SCORING_VERSION = "us-006-v1"


class PriorityLevel(StrEnum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    WATCH = "watch"
    REFERENCE_ONLY = "reference_only"
    POOR_FIT = "poor_fit"


@dataclass(frozen=True, slots=True)
class ScoreComponent:
    key: str
    raw_value: float
    weighted_contribution: float
    evidence: str = ""
    missing_data: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ScoreExplanation:
    components: tuple[ScoreComponent, ...]
    missing_fields: tuple[str, ...]
    score_reducers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EventScore:
    id: UUID
    event_id: UUID
    campaign_id: UUID
    total_score: float
    priority_level: PriorityLevel
    scoring_version: str
    calculated_at: datetime
    weights_snapshot: dict[str, float]
    components: tuple[ScoreComponent, ...]
    explanation: ScoreExplanation