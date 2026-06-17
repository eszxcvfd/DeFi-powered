"""SQLAlchemy ORM — infrastructure only."""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class OrganizationRow(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # US-047: internationalization and timezone baseline
    default_locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en-US", server_default="en-US")
    default_timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC", server_default="UTC")
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
    # US-048 — connector auto-disable metadata. The
    # fields are read-only from the domain side and
    # only updated by the bounded `AutoDisableService`.
    auto_disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    auto_disabled_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    auto_disabled_by_event_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
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
    discovery_schedule_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiscoveryScheduleRow(Base):
    __tablename__ = "discovery_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    enabled_state: Mapped[str] = mapped_column(String(16), default="enabled", index=True)
    recurrence_json: Mapped[str] = mapped_column(Text, default="{}")
    source_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    template_json: Mapped[str] = mapped_column(Text, default="{}")
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_dispatched_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_dispatch_outcome: Mapped[str | None] = mapped_column(String(64), nullable=True)
    overlap_policy: Mapped[str] = mapped_column(String(32), default="skip_while_running")
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DiscoveryScheduleDispatchRow(Base):
    __tablename__ = "discovery_schedule_dispatches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    schedule_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    discovery_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiscoveryCopilotResponseRow(Base):
    __tablename__ = "discovery_copilot_responses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    response_json: Mapped[str] = mapped_column(Text, default="{}")
    provider_id: Mapped[str] = mapped_column(String(64), default="deterministic-discovery-copilot-v1")
    model_id: Mapped[str] = mapped_column(String(64), default="grounded-template-v1")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    query_expansion_set_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AiFeedbackEventRow(Base):
    """Append-only AI feedback history (US-038)."""

    __tablename__ = "ai_feedback_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    actor_key: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    prior_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QueryExpansionSetRow(Base):
    __tablename__ = "query_expansion_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    generation_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="rule")
    variants_json: Mapped[str] = mapped_column(Text, default="[]")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ScoringSuggestionSetRow(Base):
    """Governed scoring-weight suggestion sets (US-039)."""

    __tablename__ = "scoring_suggestion_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_review")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[str] = mapped_column(Text, default="")
    caution_notes_json: Mapped[str] = mapped_column(Text, default="[]")
    assumptions_json: Mapped[str] = mapped_column(Text, default="[]")
    signals_json: Mapped[str] = mapped_column(Text, default="[]")
    deltas_json: Mapped[str] = mapped_column(Text, default="[]")
    current_weights_json: Mapped[str] = mapped_column(Text, default="{}")
    proposed_weights_json: Mapped[str] = mapped_column(Text, default="{}")
    generated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight_snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CampaignScoringWeightSnapshotRow(Base):
    """Auditable campaign scoring weight versions (US-039)."""

    __tablename__ = "campaign_scoring_weight_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    weights_json: Mapped[str] = mapped_column(Text, default="{}")
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    suggestion_set_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
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
    redacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    redacted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


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
    anonymized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    anonymized_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


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
    outcome_type: Mapped[str] = mapped_column(String(32), default="")
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linked_content_draft_id: Mapped[str] = mapped_column(String(36), default="")
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


class BrowserSessionRow(Base):
    __tablename__ = "browser_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    launch_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    event_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    source_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    initial_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), default="")
    source_domain: Mapped[str] = mapped_column(String(255), default="")
    engine: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    isolation_key: Mapped[str] = mapped_column(String(128), nullable=False)
    profile_boundary: Mapped[str] = mapped_column(String(256), nullable=False)
    current_url: Mapped[str] = mapped_column(String(1024), default="")
    latest_action_summary: Mapped[str] = mapped_column(Text, default="")
    policy_reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    stop_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    debug_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    latest_artifact_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    browser_profile_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    # US-044 — browser session budget enforcement path. The
    # `BrowserSessionBudgetEnforcer` records `memory_rss_mb` and
    # `cpu_pct` samples at session start, every 30 seconds during
    # the session, and at session end. When a sample exceeds the
    # configured budget, the session is stopped safely and a
    # `browser.session.budget_exceeded` audit entry is written.
    memory_rss_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_breached: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )


class BrowserProfileRow(Base):
    __tablename__ = "browser_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_status: Mapped[str] = mapped_column(String(32), default="none")
    consent_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state_material_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CloakBrowserPolicyRow(Base):
    __tablename__ = "cloakbrowser_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    purpose_rationale: Mapped[str] = mapped_column(Text, default="")
    owner_admin_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    compliance_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_admin_actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    compliance_actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    owner_admin_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    compliance_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    pinned_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expected_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BrowserDebugArtifactRow(Base):
    __tablename__ = "browser_debug_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    capture_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, default=0)
    captured_by: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    redacted: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BrowserSessionActionRow(Base):
    __tablename__ = "browser_session_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    parameters_json: Mapped[str] = mapped_column(Text, default="{}")
    lifecycle: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BrowserActionConfirmationRow(Base):
    __tablename__ = "browser_action_confirmations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    parameters_json: Mapped[str] = mapped_column(Text, default="{}")
    preview_json: Mapped[str] = mapped_column(Text, default="{}")
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_action_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    execution_lifecycle: Mapped[str | None] = mapped_column(String(32), nullable=True)
    execution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditEntryRow(Base):
    """Append-only audit log row (US-026).

    Application point of view: rows are never updated or deleted by the product
    code. The table is tenant-scoped on organization_id and indexed for the
    most common governance filters: actor, action, target, result, and time.
    """

    __tablename__ = "audit_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    actor_role: Mapped[str] = mapped_column(String(64), default="", index=True)
    action: Mapped[str] = mapped_column(String(96), index=True, nullable=False)
    action_family: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    target_type: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    target_id: Mapped[str] = mapped_column(String(96), index=True, nullable=False)
    target_display: Mapped[str] = mapped_column(String(300), default="")
    outcome: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    request_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    session_id: Mapped[str] = mapped_column(String(64), default="")
    correlation_id: Mapped[str] = mapped_column(String(64), default="")
    client_ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(300), default="")
    workflow: Mapped[str] = mapped_column(String(64), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    metadata_redacted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserRow(Base):
    """Durable user identity (US-027)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    password_salt: Mapped[str] = mapped_column(String(64), nullable=False)
    password_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=200_000)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    disabled_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # US-047: internationalization and timezone baseline
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en-US", server_default="en-US")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC", server_default="UTC")


class OrganizationMembershipRow(Base):
    """Link between a user, an organization, and a role (US-027)."""

    __tablename__ = "organization_memberships"
    __table_args__ = (
        # SQLite supports unique constraints via UniqueConstraint, but
        # the inline string variant keeps the migration explicit.
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SessionRow(Base):
    """Server-issued session record (US-027).

    The cleartext session token is never persisted. The token_hash column
    stores the SHA-256 of the token so a database leak does not yield a
    usable session.
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    client_ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MemberInvitationRow(Base):
    """Pending invitation from an inviter to one email address (US-028).

    Invitations are scoped to one organization, one email, and one
    intended role. The cleartext token is never persisted; the
    `token_hash` column stores the SHA-256 of the cleartext token so a
    database leak does not yield a usable invitation.
    """

    __tablename__ = "member_invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    invited_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    accepted_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserNotificationRow(Base):
    """In-app notification row (US-029).

    Per-user, per-organization, per-source-record in-app alert. The
    row stores the visible title, summary, and deep-link context. The
    cleartext email body and provider payloads live in the delivery
    attempt table, not here.
    """

    __tablename__ = "user_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="unread", index=True)
    source_record_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    deep_link: Mapped[str] = mapped_column(String(1024), default="")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NotificationPreferenceRow(Base):
    """Per-user, per-type notification preferences (US-029).

    Two boolean columns cover the two channels the first slice ships:
    in-app and email. Future channels append columns or migrate to a
    JSON map without changing the existing public contract.
    """

    __tablename__ = "notification_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EventWatchlistEntryRow(Base):
    """User-scoped watch entry for a canonical event (US-030).

    Uniqueness on (organization_id, user_id, event_id) means a user
    can only watch the same event once. Removing the row stops
    reminder eligibility without mutating the canonical event or any
    related leads.
    """

    __tablename__ = "event_watchlist_entries"
    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            "event_id",
            name="uq_event_watchlist_user_event",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    reminder_at: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    reminder_note: Mapped[str] = mapped_column(String(500), default="")
    last_actor_id: Mapped[str] = mapped_column(String(128), default="")
    last_actor_role: Mapped[str] = mapped_column(String(64), default="")
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EventWatchlistHistoryRow(Base):
    """Append-only history of watchlist mutations (US-030).

    Records the actor, the before/after reminder timestamp, and an
    optional governance note for every watched, unwatched, reminder
    set, and reminder clear action.
    """

    __tablename__ = "event_watchlist_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    entry_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(64), default="")
    from_reminder_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_reminder_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class EventManualOverrideRow(Base):
    """Field-scoped manual override of a canonical event (US-031).

    A row exists only while the override is active. The unique key
    is ``(organization_id, event_id, field)`` so the same field
    can carry at most one override per event. ``source_backed_value``
    captures the latest normalized value at the time the override
    was applied so the baseline can be restored exactly when the
    override is cleared.
    """

    __tablename__ = "event_manual_overrides"
    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "event_id",
            "field",
            name="uq_event_manual_overrides_event_field",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    field: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_backed_value: Mapped[str] = mapped_column(Text, default="")
    override_value: Mapped[str] = mapped_column(Text, default="")
    value_kind: Mapped[str] = mapped_column(String(16), default="text")
    note: Mapped[str] = mapped_column(String(500), default="")
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EventChangeHistoryRow(Base):
    """Append-only change history for canonical event edits (US-031).

    One row per edit or clear-override action. The history is
    immutable from the product layer: nothing in the application
    code updates or deletes these rows.
    """

    __tablename__ = "event_change_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    value_kind: Mapped[str] = mapped_column(String(16), default="text")
    prior_value: Mapped[str] = mapped_column(Text, default="")
    new_value: Mapped[str] = mapped_column(Text, default="")
    source_backed_value: Mapped[str] = mapped_column(Text, default="")
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(64), default="")
    reason: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class NotificationDeliveryAttemptRow(Base):
    """One email-delivery attempt per notification (US-029).

    The row holds the provider correlation ID, status, redacted
    recipient, subject, and diagnostics. Provider tokens, SMTP
    secrets, and raw recipient lists are never persisted in this
    table; only what the audit log and the operator can safely see.
    """

    __tablename__ = "notification_delivery_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    notification_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_message_id: Mapped[str] = mapped_column(String(200), default="")
    recipient: Mapped[str] = mapped_column(String(320), default="")
    subject: Mapped[str] = mapped_column(String(500), default="")
    diagnostics_json: Mapped[str] = mapped_column(Text, default="{}")
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)



class BackupSnapshotRow(Base):
    """Durable backup snapshot metadata (US-040).

    Records one backup execution with its verification lifecycle. The
    cleartext backup file path, encryption keys, and restore-time
    diagnostics are never persisted on this row — only what an
    authorized operator needs to know to evaluate backup freshness
    and restore eligibility.
    """

    __tablename__ = "backup_snapshots"

    backup_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    database_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    database_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="recorded", index=True
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[str] = mapped_column(String(128), default="")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="operator", index=True)


class LiveIntegrationToggleRow(Base):
    """Explicit enablement record for a single live integration (US-040).

    The unique key is ``(organization_id, integration)`` so each
    workspace can have at most one current toggle per integration.
    The state column is constrained to ``disabled`` or ``enabled`` at
    the application layer; the database does not enforce the
    vocabulary. Approval metadata is stored alongside the state so
    audit history and the operator UI can show why and when the
    toggle was last changed.
    """

    __tablename__ = "live_integration_toggles"
    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "integration",
            name="uq_live_integration_toggles_org_integration",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    integration: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="disabled")
    previous_state: Mapped[str] = mapped_column(String(16), default="disabled")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str] = mapped_column(String(128), default="")
    approval_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CutoverEventRow(Base):
    """Append-only cutover transition history (US-040).

    Records the actor, the previous/target mode, the launch-gate
    summary, the reason, and an optional free-form note for every
    `enter_pilot_live`, `pause`, and `rollback` action. Rows are
    never updated or deleted by the product layer.
    """

    __tablename__ = "cutover_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    previous_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    new_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(64), default="")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    gate_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    gate_summary: Mapped[str] = mapped_column(Text, default="")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class WorkerHeartbeatRow(Base):
    """Last-task heartbeat per worker (US-040).

    The Dramatiq worker writes a row whenever it completes a task.
    The launch gate reads the most recent row to verify the worker
    is alive before allowing `pilot_live` entry. Only the latest
    row per `worker_id` is meaningful; the table is append-only and
    never trimmed by the product layer.
    """

    __tablename__ = "worker_heartbeats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    worker_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    last_task: Mapped[str] = mapped_column(String(96), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    organization_id: Mapped[str] = mapped_column(String(36), default="", index=True)


class AlertRuleRow(Base):
    """Durable alert rule definition (US-041).

    The unique key is ``(organization_id, name)`` so a workspace can
    carry multiple rules per metric but never two rules with the same
    name. ``is_system`` is set by the seed migration; system rules
    can be tuned (threshold/window/severity/channels/enabled) by an
    owner or admin but cannot be deleted or renamed through the
    rule management API.
    """

    __tablename__ = "alert_rules"
    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "name",
            name="uq_alert_rules_org_name",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(96), nullable=False)
    metric: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    operator: Mapped[str] = mapped_column(String(8), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="warning")
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=600)
    channels_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class AlertEventRow(Base):
    """A single firing of an alert rule (US-041).

    ``dedup_key`` is a hash of ``rule_id`` and the firing window; the
    evaluator uses it together with ``cooldown_seconds`` to suppress
    duplicate firings. ``status`` cycles through
    ``firing`` -> ``acknowledged`` -> ``resolved`` (or
    ``suppressed`` when a duplicate lands inside the cooldown).
    Payload is the sanitized, size-capped snapshot of the metric
    value at firing time; raw secret material is never persisted on
    this row.
    """

    __tablename__ = "alert_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(96), nullable=False)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="firing")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="warning")
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    dedup_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )


class MetricsExportPolicyRow(Base):
    """Per-workspace external metrics export policy (US-042).

    The row stores the configuration for every sink (Prometheus,
    OpenTelemetry, Sentry), the last export status per sink, the
    acceptance metadata, and the per-sink audit-friendly status
    markers. The row is unique on `organization_id` so a workspace
    has exactly one policy at a time.

    The policy row never stores secret material: the Prometheus
    scrape token is stored as an `argon2id` hash, and the Sentry
    DSN is stored as a reference to the secret manager entry. The
    transport layer is responsible for looking up the secret at
    export time.
    """

    __tablename__ = "metrics_export_policies"
    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            name="uq_metrics_export_policies_org",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    prometheus_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    otel_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    sentry_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    prometheus_last_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="disabled"
    )
    prometheus_last_export_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    otel_last_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="disabled"
    )
    otel_last_export_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sentry_last_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="disabled"
    )
    sentry_last_export_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class BackupRestoreRunRow(Base):
    """A single record of a restore attempt (US-043).

    The row carries enough information to prove that a
    backup can be restored within the RTO target from
    `NFR-REL-005`. The `manifest_hash` matches the
    `BackupSnapshot` `manifest_hash` when the restore is
    faithful; a mismatch means the integrity check
    failed. Raw payload, secret material, cookies, raw
    PII, and full connection strings are never stored
    on this row.
    """

    __tablename__ = "backup_restore_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    backup_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="dry_run")
    target_location: Mapped[str] = mapped_column(Text, nullable=False, default="")
    manifest_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    audit_correlation_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default=""
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class RetentionPolicyRow(Base):
    """A single per-workspace retention policy (US-043).

    The default `audit_retention_days` follows the
    `NFR-SEC-008` floor (90 days) and cannot be lowered
    below the floor. The default
    `backup_retention_days` is 30 days and is
    operator-tunable between 1 and 3650 days. The
    `prune_enabled` flag is the master switch; the
    retention prune actor refuses to run without an
    `accepted_by` recorded in the row.
    """

    __tablename__ = "retention_policies"
    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            name="uq_retention_policies_org",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    backup_retention_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )
    audit_retention_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=90
    )
    prune_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    accepted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class PerformanceSnapshotRow(Base):
    """A single record of a load-test scenario result (US-044).

    The row carries `p50_ms`, `p95_ms`, `p99_ms`, `rps`,
    `error_rate`, and `concurrent_users` for the
    scenario. The bounded harness runs the
    deterministic in-process scenario and records a
    row against the workspace. Raw secret material,
    cookies, raw PII, and full connection strings
    are never stored on this row.
    """

    __tablename__ = "performance_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scenario: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    p50_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    p95_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    p99_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    rps: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    error_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    concurrent_users: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    audit_correlation_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default=""
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class BrowserSessionSampleRow(Base):
    """A single browser session budget sample (US-044).

    The sample is recorded at session start, every
    30 seconds during the session, and at session
    end. When the `budget_pct` exceeds the configured
    threshold, the session is stopped safely and a
    `browser.session.budget_exceeded` audit entry
    is written.
    """

    __tablename__ = "browser_session_samples"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    profile_id: Mapped[str] = mapped_column(String(36), nullable=False)
    memory_rss_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cpu_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    budget_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    audited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    breach: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )


class CalendarExportTokenRow(Base):
    """A durable bounded calendar export token (US-045).

    The `token_hash` is the only durable artifact; the
    plaintext is never stored. The row is the
    authorization artifact for the
    `GET /calendar-export/{token}.ics` endpoint; the
    service resolves the user from the row, not from
    the session.
    """

    __tablename__ = "calendar_export_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    filter_json: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    audit_correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class CalendarExportAuditRow(Base):
    """A durable record of every calendar export attempt (US-045).

    The row stores a redacted IP address, a bounded
    user agent, and a request id; the secret-safe
    payload contract from `US-041` is enforced before
    persistence. The row is consumed by the operator
    panel widget and the existing admin audit log
    filter from `US-026`.
    """

    __tablename__ = "calendar_export_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    token_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    user_agent: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )


class ConnectorHealthSnapshotRow(Base):
    """A single record of a per-connector health
    computation result (US-046).

    The row carries enough information to answer
    the `FR-ADM-002` question "is connector X
    healthy right now?" without reading raw
    tables. The secret-safe payload contract
    from `US-041` is enforced before persistence.
    """

    __tablename__ = "connector_health_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    connector_type: Mapped[str] = mapped_column(String(32), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p50_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p95_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    captcha_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    captcha_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    audit_correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class ConnectorHealthErrorRow(Base):
    """A single record of a recent error rollup
    (US-046).

    The table is bounded to the most recent N
    errors per source so a single failing
    connector cannot fill the table. The
    secret-safe payload contract from `US-041`
    is enforced before persistence.
    """

    __tablename__ = "connector_health_errors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    error_code: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    audit_correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )


class ConnectorAutoDisableRuleRow(Base):
    """A per-source auto-disable policy
    (US-048).

    The row carries enough information for the
    bounded `AutoDisableService` to evaluate a
    source against the closed trigger rules
    without reading raw tables. The secret-safe
    payload contract from `US-041` is enforced
    before persistence.
    """

    __tablename__ = "connector_auto_disable_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=1800)
    consecutive_breaches: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=900)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class ConnectorAutoDisableEventRow(Base):
    """A per-event auto-disable history
    (US-048).

    The row records the bounded auto-disable
    lifecycle. The table is bounded to the most
    recent N events per source so a flapping
    connector cannot fill the table. The
    secret-safe payload contract from `US-041`
    is enforced before persistence.
    """

    __tablename__ = "connector_auto_disable_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    breach_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    alert_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    health_snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recovery_actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recovery_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    audit_correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )


class WebhookSubscriptionRow(Base):
    """A per-workspace webhook subscription
    (US-049).

    The row carries enough information for the
    bounded `WebhookDeliveryService` to
    dispatch a delivery against the closed
    retry policy without reading raw tables.
    The secret-safe payload contract from
    `US-041` is enforced before persistence.
    """

    __tablename__ = "webhook_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    event_types_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )
    last_rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class WebhookSigningSecretRow(Base):
    """A per-subscription signing secret
    (US-049).

    The secret is stored encrypted via the
    `US-003` `SecretVault`; the bounded
    service never returns the plaintext in
    any response payload.
    """

    __tablename__ = "webhook_signing_secrets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subscription_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    secret_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class WebhookDeliveryRow(Base):
    """A per-delivery webhook history
    (US-049).

    The table is bounded to the most recent N
    deliveries per subscription so a flapping
    subscription cannot fill the table. The
    secret-safe payload contract from
    `US-041` is enforced before persistence.
    """

    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subscription_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    signature: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_response_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )


class LeadImportJobRow(Base):
    """A preview/apply CSV import job (US-050).

    The row carries the bounded slice of metadata
    needed to reconstruct the preview and audit
    the apply, plus the file hash and provenance
    note. The raw CSV blob is never persisted; the
    preview is the durable surface.
    """

    __tablename__ = "lead_import_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False, default="viewer")
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    delimiter: Mapped[str] = mapped_column(String(4), nullable=False)
    mapping_json: Mapped[str] = mapped_column(Text, nullable=False)
    provenance_note: Mapped[str] = mapped_column(Text, nullable=False)
    campaign_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ready_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LeadImportRowRow(Base):
    """One previewed/imported CSV row (US-050).

    The row keeps the normalized payload and the
    classification result so the preview UI and the
    apply stage share the same snapshot.
    """

    __tablename__ = "lead_import_rows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    import_job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    normalized_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[str] = mapped_column(
        String(32), nullable=False, default="invalid"
    )
    duplicate_lead_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    duplicate_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error_codes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_lead_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )
