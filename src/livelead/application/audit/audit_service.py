"""Audit application service (US-026).

Public boundary used by REST routes to emit normalized audit entries and to
support read-side list/detail queries. Writes are best-effort: a failed audit
write must not break the originating workflow, so emit() swallows and logs
exceptions instead of propagating them.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

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
    normalize_entry,
)
from livelead.infrastructure.db.audit_mappers import row_to_audit_entry
from livelead.infrastructure.db.models import AuditEntryRow
from livelead.infrastructure.db.repositories.audit_log import AuditEntryRepository

logger = logging.getLogger("livelead.audit")


class AuditEmitError(Exception):
    """Raised by callers that need strict audit semantics (tests/CLI)."""


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AuditEntryRepository(session)

    async def emit(
        self,
        *,
        organization_id: UUID,
        actor: AuditActor,
        action: AuditAction,
        target: AuditTarget,
        outcome: AuditOutcome,
        context: AuditContext,
        metadata: dict[str, Any] | None = None,
        occurred_at: datetime | None = None,
    ) -> AuditEntry | None:
        """Build, persist, and return a normalized audit entry.

        Returns ``None`` if persistence failed but the workflow must continue.
        Use ``emit_strict`` in callers that need to assert the write happened.
        """

        entry = normalize_entry(
            organization_id=organization_id,
            actor=actor,
            action=action,
            target=target,
            outcome=outcome,
            context=context,
            metadata=metadata,
            occurred_at=occurred_at,
        )
        try:
            row = AuditEntryRow(
                id=str(entry.id),
                organization_id=str(entry.organization_id),
                actor_id=entry.actor.actor_id,
                actor_type=entry.actor.actor_type.value,
                actor_role=entry.actor.role or "",
                action=entry.action.value,
                action_family=entry.action_family,
                target_type=entry.target.target_type.value,
                target_id=entry.target.target_id,
                target_display=entry.target.display or "",
                outcome=entry.outcome.value,
                occurred_at=entry.occurred_at,
                request_id=entry.context.request_id or "",
                session_id=entry.context.session_id or "",
                correlation_id=entry.context.correlation_id or "",
                client_ip=entry.context.ip or "",
                user_agent=(entry.context.user_agent or "")[:300],
                workflow=entry.context.workflow or "",
                metadata_json=__import__("json").dumps(entry.metadata, default=str),
                metadata_redacted=entry.metadata_redacted,
            )
            await self._repo.add(row)
            return entry
        except Exception as exc:  # pragma: no cover - defensive, tested via integration
            logger.warning("audit_emit_failed action=%s err=%s", action.value, exc)
            return None

    async def emit_strict(self, **kwargs) -> AuditEntry:
        entry = await self.emit(**kwargs)
        if entry is None:
            raise AuditEmitError(f"failed to emit audit action={kwargs.get('action')}")
        return entry

    async def emit_login_outcome(
        self,
        *,
        organization_id: UUID,
        actor_id: str,
        outcome: AuditOutcome,
        request_id: str = "",
        ip: str = "",
        user_agent: str = "",
        reason: str = "",
    ) -> AuditEntry | None:
        action = (
            AuditAction.LOGIN_SUCCEEDED
            if outcome == AuditOutcome.SUCCEEDED
            else AuditAction.LOGIN_FAILED
        )
        actor = AuditActor(actor_id=actor_id or "anonymous", actor_type=AuditActorType.HUMAN, role="")
        target = AuditTarget(
            target_type=AuditTargetType.USER, target_id=actor_id or "anonymous", display=actor_id or "anonymous"
        )
        return await self.emit(
            organization_id=organization_id,
            actor=actor,
            action=action,
            target=target,
            outcome=outcome,
            context=AuditContext(request_id=request_id, ip=ip, user_agent=user_agent, workflow="login"),
            metadata={"reason": reason} if reason else {},
        )

    async def list_entries(
        self,
        organization_id: UUID,
        *,
        actor_id: str | None = None,
        actor_type: str | None = None,
        action: str | None = None,
        action_family: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        outcome: str | None = None,
        request_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditEntry], int]:
        rows, total = await self._repo.list_for_org(
            organization_id,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            action_family=action_family,
            target_type=target_type,
            target_id=target_id,
            outcome=outcome,
            request_id=request_id,
            since=since,
            until=until,
            limit=limit,
            offset=offset,
        )
        return [row_to_audit_entry(r) for r in rows], total

    async def get_entry(
        self, entry_id: UUID, organization_id: UUID
    ) -> AuditEntry | None:
        row = await self._repo.get_for_org(entry_id, organization_id)
        return row_to_audit_entry(row) if row else None


def make_actor_from_role(actor_role: str, actor_id: str | None = None) -> AuditActor:
    role = (actor_role or "system").strip().lower() or "system"
    if role in {"system", "service"}:
        return AuditActor(actor_id=actor_id or role, actor_type=AuditActorType(role), role=role)
    return AuditActor(actor_id=actor_id or role, actor_type=AuditActorType.HUMAN, role=role)


def make_context(
    *,
    request_id: str = "",
    session_id: str = "",
    correlation_id: str = "",
    ip: str = "",
    user_agent: str = "",
    workflow: str = "",
) -> AuditContext:
    return AuditContext(
        request_id=(request_id or "")[:64],
        session_id=(session_id or "")[:64],
        correlation_id=(correlation_id or "")[:64],
        ip=(ip or "")[:64],
        user_agent=(user_agent or "")[:300],
        workflow=(workflow or "")[:64],
    )


def new_correlation_id() -> str:
    return str(uuid4())
