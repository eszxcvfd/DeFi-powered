"""Audit ORM -> domain mapping (US-026)."""

from __future__ import annotations

from livelead.domain.audit.enums import (
    AuditAction,
    AuditActorType,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import (
    AuditActor,
    AuditContext,
    AuditEntry,
    AuditTarget,
)
from livelead.infrastructure.db.models import AuditEntryRow
from livelead.infrastructure.db.repositories.audit_log import AuditEntryRepository


def _enum(value, enum_cls, default):
    try:
        return enum_cls(value)
    except (ValueError, TypeError):
        return default


def row_to_audit_entry(row: AuditEntryRow) -> AuditEntry:
    return AuditEntry(
        id=row.id if isinstance(row.id, type(__import__("uuid").UUID)) else __import__("uuid").UUID(str(row.id)),
        organization_id=row.organization_id
        if isinstance(row.organization_id, type(__import__("uuid").UUID))
        else __import__("uuid").UUID(str(row.organization_id)),
        actor=AuditActor(
            actor_id=row.actor_id,
            actor_type=_enum(row.actor_type, AuditActorType, AuditActorType.HUMAN),
            role=row.actor_role or "",
        ),
        action=_enum(row.action, AuditAction, AuditAction.SOURCE_POLICY_CHANGED),
        target=AuditTarget(
            target_type=_enum(row.target_type, AuditTargetType, AuditTargetType.SYSTEM),
            target_id=row.target_id,
            display=row.target_display or "",
        ),
        outcome=_enum(row.outcome, AuditOutcome, AuditOutcome.SUCCEEDED),
        occurred_at=row.occurred_at,
        context=AuditContext(
            request_id=row.request_id or "",
            session_id=row.session_id or "",
            correlation_id=row.correlation_id or "",
            ip=row.client_ip or "",
            user_agent=row.user_agent or "",
            workflow=row.workflow or "",
        ),
        metadata=AuditEntryRepository.metadata_json(row),
        metadata_redacted=bool(row.metadata_redacted),
    )
