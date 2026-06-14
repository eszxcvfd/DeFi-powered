"""Browser session domain types (US-020)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class BrowserSessionState(StrEnum):
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    NEEDS_USER_ACTION = "needs_user_action"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class BrowserEngine(StrEnum):
    PLAYWRIGHT = "playwright"
    SELENIUM = "selenium"
    CLOAKBROWSER = "cloakbrowser"
    STUB = "stub"


class LaunchContextKind(StrEnum):
    EVENT = "event"
    SOURCE = "source"


@dataclass(frozen=True, slots=True)
class BrowserSessionTarget:
    kind: LaunchContextKind
    event_id: UUID | None
    source_id: UUID
    initial_url: str
    source_name: str
    source_domain: str


@dataclass(frozen=True, slots=True)
class BrowserSessionIsolation:
    isolation_key: str
    profile_boundary: str
    engine: BrowserEngine


@dataclass(frozen=True, slots=True)
class BrowserSessionRecord:
    id: UUID
    organization_id: UUID
    actor: str
    state: BrowserSessionState
    engine: BrowserEngine
    target: BrowserSessionTarget
    isolation: BrowserSessionIsolation
    current_url: str
    latest_action_summary: str
    policy_reasons: tuple[str, ...]
    stop_requested: bool
    error_summary: str | None
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None
    worker_id: str | None
    debug_enabled: bool = False
    latest_artifact_summary: str = ""
