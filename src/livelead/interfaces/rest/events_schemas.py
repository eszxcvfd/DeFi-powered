from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ScoreComponentSchema(BaseModel):
    key: str
    raw_value: float
    weighted_contribution: float
    evidence: str = ""
    missing_data: list[str] = Field(default_factory=list)


class EventScoreSummarySchema(BaseModel):
    total_score: float | None = None
    priority_level: str | None = None
    scoring_version: str | None = None
    calculated_at: datetime | None = None
    score_state: str = "missing"


class FieldConfidenceSchema(BaseModel):
    field: str
    trust: str
    note: str = ""


class EventProvenanceSchema(BaseModel):
    confidence_summary: str = "medium"
    field_confidence: list[FieldConfidenceSchema] = Field(default_factory=list)
    merge_notes: list[dict] = Field(default_factory=list)
    observation_count: int = 1
    source_ids: list[UUID] = Field(default_factory=list)


class EventListItemSchema(BaseModel):
    id: UUID
    campaign_id: UUID
    canonical_title: str
    source_url: str
    observed_at: datetime
    region: str = ""
    confidence_summary: str = "medium"
    observation_count: int = 1
    source_count: int = 1
    discovery_job_id: UUID | None = None
    score: EventScoreSummarySchema | None = None
    deferred: dict[str, str] = Field(default_factory=lambda: {"scoring": "available"})


class EventSourceObservationSchema(BaseModel):
    id: UUID
    source_id: UUID
    source_url: str
    observed_at: datetime
    raw_title: str
    discovery_job_id: UUID | None = None


class EventScoreDetailSchema(BaseModel):
    total_score: float
    priority_level: str
    scoring_version: str
    calculated_at: datetime
    weights_snapshot: dict[str, float]
    components: list[ScoreComponentSchema]
    missing_fields: list[str] = Field(default_factory=list)
    score_reducers: list[str] = Field(default_factory=list)


class AudienceEvidenceSchema(BaseModel):
    cue: str
    kind: str
    detail: str
    source_field: str = ""


class AudienceHypothesisSchema(BaseModel):
    id: UUID
    segment_name: str
    fit_type: str
    reason: str
    confidence: float
    generated_by: str
    model_version: str
    evidence: list[AudienceEvidenceSchema]


class AudienceAnalysisSchema(BaseModel):
    state: str
    hypotheses: list[AudienceHypothesisSchema] = Field(default_factory=list)
    generation_notes: list[str] = Field(default_factory=list)
    strategy_version: str = ""


class EventDetailSchema(BaseModel):
    id: UUID
    campaign_id: UUID
    canonical_title: str
    source_url: str
    observed_at: datetime
    description: str = ""
    organizer: str = ""
    region: str = ""
    starts_at: datetime | None = None
    discovery_job_id: UUID | None = None
    provenance: EventProvenanceSchema
    observations: list[EventSourceObservationSchema]
    score: EventScoreDetailSchema | None = None
    score_state: str = "missing"
    audience: AudienceAnalysisSchema
    deferred: dict[str, str] = Field(
        default_factory=lambda: {
            "audience_feedback": "planned",
            "engagement": "planned",
            "leads": "planned",
            "browser": "planned",
        }
    )