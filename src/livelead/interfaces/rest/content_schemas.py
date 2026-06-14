from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ContentGenerationSettingsSchema(BaseModel):
    content_type: str = "outreach"
    platform: str = "email"
    language: str = "en"
    tone: str = "professional"
    length: str = "medium"
    market_context: str = ""
    cta: str = "Learn more"
    variant_count: int = 2


class ContentGenerateRequestSchema(BaseModel):
    event_id: UUID
    settings: ContentGenerationSettingsSchema = Field(
        default_factory=ContentGenerationSettingsSchema
    )


class ContentRiskFlagSchema(BaseModel):
    code: str
    message: str
    severity: str = "warning"


class ContentDraftSummarySchema(BaseModel):
    id: UUID
    variant_index: int
    content_type: str
    platform: str
    lifecycle: str
    body_preview: str
    risk_flag_count: int
    last_editor: str
    updated_at: datetime | None = None


class ContentHandoffRecordSchema(BaseModel):
    id: UUID
    action: str
    actor: str
    export_format: str = ""
    body_revision: int
    created_at: datetime


class ContentReviewDecisionSchema(BaseModel):
    id: UUID
    action: str
    from_status: str
    to_status: str
    actor: str
    note: str = ""
    body_revision: int
    created_at: datetime


class ContentDraftDetailSchema(BaseModel):
    id: UUID
    event_id: UUID
    variant_index: int
    review_status: str
    body_revision: int = 1
    reviewer_assignee: str = ""
    ready_for_use: bool = False
    usage_status: str = "not_used"
    handoff_available: bool = False
    export_formats: list[str] = Field(default_factory=lambda: ["markdown", "csv"])
    latest_handoff_at: datetime | None = None
    latest_handoff_actor: str = ""
    settings: ContentGenerationSettingsSchema
    body_text: str
    risk_flags: list[ContentRiskFlagSchema]
    provider: str
    model: str
    prompt_template_version: str
    input_context_summary: str
    last_editor: str
    generated_at: datetime | None = None
    updated_at: datetime | None = None
    review_history: list[ContentReviewDecisionSchema] = Field(default_factory=list)
    handoff_history: list[ContentHandoffRecordSchema] = Field(default_factory=list)


class ContentContextPreviewSchema(BaseModel):
    event_title: str
    event_description: str
    campaign_focus: str
    score_summary: str
    audience_summary: str
    plan_task_count: int
    notes: list[str] = Field(default_factory=list)


class ContentGenerateResponseSchema(BaseModel):
    context: ContentContextPreviewSchema
    drafts: list[ContentDraftDetailSchema]


class ContentDraftPatchSchema(BaseModel):
    body_text: str
    editor: str = "analyst"


class ContentReviewActionSchema(BaseModel):
    event_id: UUID
    note: str = ""
    actor: str = "reviewer"


class ContentSubmitReviewSchema(BaseModel):
    assignee: str = ""


class ContentHandoffActionSchema(BaseModel):
    event_id: UUID
    actor: str = "analyst"
