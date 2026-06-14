"""SQLAlchemy ORM — infrastructure only."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class OrganizationRow(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CampaignRow(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    target_industry: Mapped[str] = mapped_column(String(200), default="")
    product_or_service_focus: Mapped[str] = mapped_column(String(200), default="")
    market_regions_json: Mapped[str] = mapped_column(Text, default="[]")
    languages_json: Mapped[str] = mapped_column(Text, default="[]")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    date_start: Mapped[str | None] = mapped_column(String(10), nullable=True)
    date_end: Mapped[str | None] = mapped_column(String(10), nullable=True)
    positive_keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    exclude_keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    icp_json: Mapped[str] = mapped_column(Text, default="{}")
    scoring_weights_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    parent_campaign_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_by_actor: Mapped[str] = mapped_column(String(128), default="analyst")
    creation_source: Mapped[str] = mapped_column(String(64), default="user", index=True)
    automation_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    connector_type: Mapped[str] = mapped_column(String(32), nullable=False)
    automation_engine: Mapped[str] = mapped_column(String(64), default="none")
    authentication_mode: Mapped[str] = mapped_column(String(32), default="none")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    policy_json: Mapped[str] = mapped_column(Text, default="{}")
    rate_limit_json: Mapped[str] = mapped_column(Text, default="{}")
    secret_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CampaignSourceRow(Base):
    __tablename__ = "campaign_sources"

    campaign_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)


class DiscoveryJobRow(Base):
    __tablename__ = "discovery_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    criteria_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    progress_json: Mapped[str] = mapped_column(Text, default="{}")
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventRow(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    canonical_title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    organizer: Mapped[str] = mapped_column(String(300), default="")
    region: Mapped[str] = mapped_column(String(120), default="")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    discovery_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventSourceObservationRow(Base):
    __tablename__ = "event_source_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_title: Mapped[str] = mapped_column(String(500), default="")
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    discovery_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AudienceHypothesisRow(Base):
    __tablename__ = "audience_hypotheses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    segment_name: Mapped[str] = mapped_column(String(300), nullable=False)
    fit_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EngagementPlanRow(Base):
    __tablename__ = "engagement_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    generation_notes_json: Mapped[str] = mapped_column(Text, default="[]")
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EngagementTaskRow(Base):
    __tablename__ = "engagement_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    plan_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    assignee: Mapped[str] = mapped_column(String(128), default="")
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GeneratedContentDraftRow(Base):
    __tablename__ = "generated_content_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    engagement_plan_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    variant_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifecycle: Mapped[str] = mapped_column(String(32), default="draft")
    settings_json: Mapped[str] = mapped_column(Text, default="{}")
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    risk_flags_json: Mapped[str] = mapped_column(Text, default="[]")
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_template_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_context_summary: Mapped[str] = mapped_column(Text, default="")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_editor: Mapped[str] = mapped_column(String(128), default="system")
    body_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reviewer_assignee: Mapped[str] = mapped_column(String(128), default="")
    usage_status: Mapped[str] = mapped_column(String(32), default="not_used")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ContentReviewDecisionRow(Base):
    __tablename__ = "content_review_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    draft_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="")
    body_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContentHandoffRecordRow(Base):
    __tablename__ = "content_handoff_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    draft_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    export_format: Mapped[str] = mapped_column(String(32), default="")
    body_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LeadRow(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    campaign_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String(300), nullable=False)
    company: Mapped[str] = mapped_column(String(300), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    public_url: Mapped[str] = mapped_column(String(1024), default="")
    discovery_source: Mapped[str] = mapped_column(String(200), default="")
    event_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    interests: Mapped[str] = mapped_column(Text, default="")
    pain_points: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(128), default="")
    stage: Mapped[str] = mapped_column(String(32), default="newly_discovered", index=True)
    lawful_basis_note: Mapped[str] = mapped_column(Text, default="")
    follow_up_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    manual_entry_note: Mapped[str] = mapped_column(Text, default="")
    origin_kind: Mapped[str] = mapped_column(String(32), default="event")
    email_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    external_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    created_by: Mapped[str] = mapped_column(String(128), default="analyst")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FollowUpReminderRow(Base):
    __tablename__ = "follow_up_reminders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    lead_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    owner: Mapped[str] = mapped_column(String(128), default="")
    due_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), default="scheduled", index=True)
    last_actor: Mapped[str] = mapped_column(String(128), default="")
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ReminderHistoryRow(Base):
    __tablename__ = "reminder_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    reminder_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    lead_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="")
    from_due_date: Mapped[str] = mapped_column(String(10), default="")
    to_due_date: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LeadActivityRow(Base):
    __tablename__ = "lead_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    lead_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    from_stage: Mapped[str] = mapped_column(String(32), default="")
    to_stage: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventScoreRow(Base):
    __tablename__ = "event_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority_level: Mapped[str] = mapped_column(String(32), nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(64), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    weights_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    components_json: Mapped[str] = mapped_column(Text, default="[]")
    explanation_json: Mapped[str] = mapped_column(Text, default="{}")
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)