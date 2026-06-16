"""Governed AI feedback domain types (US-038)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class AiFeedbackTargetType(StrEnum):
    DISCOVERY_COPILOT_RESPONSE = "discovery_copilot_response"
    AUDIENCE_HYPOTHESIS = "audience_hypothesis"


class DiscoveryCopilotFeedbackState(StrEnum):
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"


class AudienceHypothesisFeedbackState(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    UNCERTAIN = "uncertain"


class AiFeedbackReasonCode(StrEnum):
    LOW_EVIDENCE = "low_evidence"
    WRONG_AUDIENCE_FIT = "wrong_audience_fit"
    WEAK_USEFULNESS = "weak_usefulness"
    MISLEADING = "misleading"
    OTHER = "other"


NOTE_MAX_LEN = 500


@dataclass(frozen=True, slots=True)
class AiFeedbackProjection:
    target_type: AiFeedbackTargetType
    target_id: UUID
    state: str
    reason_code: str | None
    note: str | None
    actor_key: str
    updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class AiFeedbackAggregate:
    helpful_count: int = 0
    not_helpful_count: int = 0
    correct_count: int = 0
    incorrect_count: int = 0
    uncertain_count: int = 0