"""Engagement plan domain types."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

ENGAGEMENT_STRATEGY_VERSION = "us-008-v1"


class EngagementPhase(StrEnum):
    PRE_EVENT = "PRE_EVENT"
    LIVE_EVENT = "LIVE_EVENT"
    POST_EVENT = "POST_EVENT"


class EngagementTaskStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class EngagementTask:
    id: UUID
    plan_id: UUID
    event_id: UUID
    phase: EngagementPhase
    title: str
    rationale: str
    status: EngagementTaskStatus
    assignee: str = ""
    deadline: datetime | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class EngagementPlan:
    id: UUID
    event_id: UUID
    campaign_id: UUID
    strategy_version: str
    generation_notes: tuple[str, ...] = ()
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class EngagementPlanState:
    state: str  # missing | ready | blocked
    plan: EngagementPlan | None = None
    tasks: tuple[EngagementTask, ...] = ()
    generation_notes: tuple[str, ...] = ()
