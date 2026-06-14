"""Audience hypothesis domain types."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

AUDIENCE_STRATEGY_VERSION = "us-007-v1"


class FitType(StrEnum):
    CUSTOMER = "customer"
    PARTNER = "partner"
    REFERRAL = "referral"


class EvidenceKind(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"


@dataclass(frozen=True, slots=True)
class AudienceEvidenceItem:
    cue: str
    kind: EvidenceKind
    detail: str
    source_field: str = ""


@dataclass(frozen=True, slots=True)
class AudienceHypothesis:
    id: UUID
    event_id: UUID
    segment_name: str
    fit_type: FitType
    reason: str
    confidence: float
    generated_by: str
    model_version: str
    evidence: tuple[AudienceEvidenceItem, ...]
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AudienceAnalysisState:
    state: str  # ready | empty | pending | blocked
    hypotheses: tuple[AudienceHypothesis, ...] = ()
    generation_notes: tuple[str, ...] = ()
    strategy_version: str = AUDIENCE_STRATEGY_VERSION