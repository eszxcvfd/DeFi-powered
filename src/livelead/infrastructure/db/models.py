"""SQLAlchemy ORM — infrastructure only."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, String, Text, func
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