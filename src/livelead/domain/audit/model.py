"""Audit domain model and normalization rules (US-026)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from livelead.domain.audit.enums import (
    AuditAction,
    AuditActorType,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.redaction import (
    enforce_size_cap,
    is_sensitive_key,
    redact_metadata,
)

# Action family: dotted first segment of an action. e.g. "content.review.approved" -> "content".
_ACTION_FAMILY_RE = re.compile(r"^([a-z_]+)\.")


def action_family(action: AuditAction | str) -> str:
    raw = action.value if isinstance(action, AuditAction) else str(action)
    m = _ACTION_FAMILY_RE.match(raw)
    return m.group(1) if m else raw


@dataclass(frozen=True, slots=True)
class AuditActor:
    actor_id: str
    actor_type: AuditActorType
    role: str = ""

    def __post_init__(self) -> None:
        if not self.actor_id:
            raise ValueError("actor_id is required")
        if not isinstance(self.actor_type, AuditActorType):
            raise ValueError("actor_type must be AuditActorType")


@dataclass(frozen=True, slots=True)
class AuditTarget:
    target_type: AuditTargetType
    target_id: str
    display: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.target_type, AuditTargetType):
            raise ValueError("target_type must be AuditTargetType")
        if not self.target_id:
            raise ValueError("target_id is required")


@dataclass(frozen=True, slots=True)
class AuditContext:
    request_id: str = ""
    session_id: str = ""
    correlation_id: str = ""
    ip: str = ""
    user_agent: str = ""
    workflow: str = ""

    def safe_dict(self) -> dict[str, str]:
        return {
            k: v
            for k, v in {
                "request_id": self.request_id,
                "session_id": self.session_id,
                "correlation_id": self.correlation_id,
                "ip": self.ip,
                "user_agent": self.user_agent,
                "workflow": self.workflow,
            }.items()
            if v
        }


@dataclass(frozen=True, slots=True)
class AuditEntry:
    id: UUID
    organization_id: UUID
    actor: AuditActor
    action: AuditAction
    target: AuditTarget
    outcome: AuditOutcome
    occurred_at: datetime
    context: AuditContext
    metadata: dict[str, Any] = field(default_factory=dict)
    metadata_redacted: bool = False

    @property
    def action_family(self) -> str:
        return action_family(self.action)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "actor": {
                "actor_id": self.actor.actor_id,
                "actor_type": self.actor.actor_type.value,
                "role": self.actor.role,
            },
            "action": self.action.value,
            "action_family": self.action_family,
            "target": {
                "target_type": self.target.target_type.value,
                "target_id": self.target.target_id,
                "display": self.target.display,
            },
            "outcome": self.outcome.value,
            "occurred_at": self.occurred_at.isoformat(),
            "context": self.context.safe_dict(),
            "metadata": self.metadata,
            "metadata_redacted": self.metadata_redacted,
        }


def _now() -> datetime:
    return datetime.now(UTC)


def normalize_entry(
    *,
    organization_id: UUID,
    actor: AuditActor,
    action: AuditAction,
    target: AuditTarget,
    outcome: AuditOutcome,
    context: AuditContext,
    metadata: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> AuditEntry:
    """Build a single AuditEntry with redacted, size-capped metadata.

    Pure function — no I/O. The repository layer is responsible for persistence.
    """

    raw_metadata = metadata or {}
    if not isinstance(raw_metadata, dict):
        raw_metadata = {"value": str(raw_metadata)}
    redacted = redact_metadata(raw_metadata)
    redacted = enforce_size_cap(redacted)
    # Note when redaction removed fields so operators understand why metadata is partial.
    redacted_flag = any(
        is_sensitive_key(str(k)) for k in raw_metadata
    ) or redacted.get("truncated") is True

    return AuditEntry(
        id=uuid4(),
        organization_id=organization_id,
        actor=actor,
        action=action,
        target=target,
        outcome=outcome,
        occurred_at=occurred_at or _now(),
        context=context,
        metadata=redacted,
        metadata_redacted=redacted_flag,
    )


def make_system_actor(actor_id: str = "system", role: str = "system") -> AuditActor:
    return AuditActor(actor_id=actor_id, actor_type=AuditActorType.SYSTEM, role=role)


def make_service_actor(actor_id: str, role: str = "service") -> AuditActor:
    return AuditActor(actor_id=actor_id, actor_type=AuditActorType.SERVICE, role=role)
