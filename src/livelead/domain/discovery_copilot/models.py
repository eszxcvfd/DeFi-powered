"""Discovery copilot structured response model (US-037)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CopilotRiskCode(StrEnum):
    WEAK_EVIDENCE = "weak_evidence"
    LOW_CONFIDENCE = "low_confidence"
    MISSING_SOURCE_COVERAGE = "missing_source_coverage"
    UNGROUNDED_QUESTION = "ungrounded_question"
    SENSITIVE_INFERENCE = "sensitive_inference"


@dataclass(frozen=True)
class CopilotClaim:
    text: str
    confidence: float | None = None


@dataclass(frozen=True)
class CopilotEvidence:
    summary: str
    source_ref: str | None = None


@dataclass(frozen=True)
class CopilotRiskFlag:
    code: str
    message: str


@dataclass
class DiscoveryCopilotStructuredResponse:
    claims: list[CopilotClaim] = field(default_factory=list)
    evidence: list[CopilotEvidence] = field(default_factory=list)
    confidence: float = 0.0
    assumptions: list[str] = field(default_factory=list)
    risk_flags: list[CopilotRiskFlag] = field(default_factory=list)
    proposed_query_framing: list[str] = field(default_factory=list)
    recommended_source_ids: list[str] = field(default_factory=list)
    provider_id: str = "deterministic-discovery-copilot-v1"
    model_id: str = "grounded-template-v1"