"""Generated content domain types."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

CONTENT_TEMPLATE_VERSION = "us-009-v1"
DEFAULT_PROVIDER = "deterministic_local"


class ContentType(StrEnum):
    OUTREACH = "outreach"
    FOLLOW_UP = "follow_up"
    EVENT_INTRO = "event_intro"
    VALUE_NOTE = "value_note"


class ContentPlatform(StrEnum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    SLACK = "slack"


class RiskFlagCode(StrEnum):
    OVERLY_PROMOTIONAL = "overly_promotional"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    SENSITIVE_TARGETING = "sensitive_targeting"
    LACKS_EVENT_RELEVANCE = "lacks_event_relevance"
    UNSUITABLE_CTA = "unsuitable_cta"
    REPETITIVE = "repetitive"


class ContentReviewStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ContentUsageStatus(StrEnum):
    NOT_USED = "not_used"
    USED = "used"


# Alias for generation defaults
DraftLifecycle = ContentReviewStatus


@dataclass(frozen=True, slots=True)
class ContentGenerationSettings:
    content_type: ContentType
    platform: ContentPlatform
    language: str = "en"
    tone: str = "professional"
    length: str = "medium"
    market_context: str = ""
    cta: str = "Learn more"
    variant_count: int = 2


@dataclass(frozen=True, slots=True)
class ContentRiskFlag:
    code: RiskFlagCode
    message: str
    severity: str = "warning"


@dataclass(frozen=True, slots=True)
class GenerationMetadata:
    provider: str
    model: str
    prompt_template_version: str
    input_context_summary: str
    generated_at: datetime
    last_editor: str = "system"


@dataclass(frozen=True, slots=True)
class GeneratedContentDraft:
    id: UUID
    event_id: UUID
    campaign_id: UUID
    engagement_plan_id: UUID | None
    variant_index: int
    review_status: ContentReviewStatus
    settings: ContentGenerationSettings
    body_text: str
    body_revision: int = 1
    reviewer_assignee: str = ""
    usage_status: ContentUsageStatus = ContentUsageStatus.NOT_USED
    risk_flags: tuple[ContentRiskFlag, ...] = ()
    metadata: GenerationMetadata | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ContentReviewDecision:
    id: UUID
    draft_id: UUID
    event_id: UUID
    action: str  # submit | approve | reject
    from_status: str
    to_status: str
    actor: str
    note: str
    body_revision: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ContentHandoffRecord:
    id: UUID
    draft_id: UUID
    event_id: UUID
    action: str  # copy | export | mark_used
    actor: str
    export_format: str = ""
    body_revision: int = 1
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ContentContextPreview:
    event_title: str
    event_description: str
    campaign_focus: str
    score_summary: str
    audience_summary: str
    plan_task_count: int
    notes: tuple[str, ...] = ()
