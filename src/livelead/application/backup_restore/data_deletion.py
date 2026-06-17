"""Data deletion application service (US-043).

Owns the governed data-deletion path. The service is
the only place that deletes or anonymizes a lead, a
user, or a source observation; the REST layer calls
it from the request handlers.

The service is intentionally conservative: every
deletion marks the record as `anonymized` or
`redacted` rather than cascading delete. The cascade
is the caller's responsibility; the service emits a
separate audit entry for each step.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.application.backup_restore.service import (
    BackupRestoreError,
    _safe_metadata,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditTarget
from livelead.domain.backup.enums import DataDeletionTarget
from livelead.domain.backup.models import (
    validate_data_deletion_request,
)
from livelead.infrastructure.db.models import (
    EventSourceObservationRow,
    LeadRow,
    UserRow,
)

logger = logging.getLogger("livelead.data_deletion_service")


class DataDeletionService:
    """Application service for the governed data-deletion surface.

    The service is the only writer of the
    `anonymized_at` and `redacted_at` columns on the
    `LeadRow`, `UserRow`, and `EventSourceObservationRow`
    tables. The service refuses to run without an
    `accepted_by` and a `reason` recorded in the
    request payload.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        audit_service: AuditService | None = None,
    ) -> None:
        self._session = session
        self._audit = audit_service or AuditService(session)

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def delete_data(
        self,
        *,
        organization_id: UUID | str,
        target: DataDeletionTarget | str,
        target_id: str,
        accepted_by: str,
        reason: str,
        actor: str = "system",
        actor_role: str = "system",
    ) -> dict[str, Any]:
        """Run a governed data-deletion request.

        The service refuses to run without an
        `accepted_by` and a `reason` recorded in the
        request payload. The service marks the
        record as `anonymized` or `redacted` rather
        than cascading delete.
        """

        try:
            validate_data_deletion_request(
                target=target,
                target_id=target_id,
                accepted_by=accepted_by,
                reason=reason,
            )
        except ValueError as exc:
            raise BackupRestoreError(str(exc)) from exc
        target_value = (
            target.value if isinstance(target, DataDeletionTarget) else str(target)
        )
        target_enum = DataDeletionTarget(target_value)
        org = str(organization_id)
        now = datetime.utcnow()
        if target_enum is DataDeletionTarget.LEAD:
            outcome = await self._anonymize_lead(
                organization_id=org,
                lead_id=target_id,
                accepted_by=accepted_by,
                reason=reason,
                actor=actor,
                actor_role=actor_role,
                now=now,
            )
        elif target_enum is DataDeletionTarget.USER:
            outcome = await self._disable_user(
                organization_id=org,
                user_id=target_id,
                accepted_by=accepted_by,
                reason=reason,
                actor=actor,
                actor_role=actor_role,
                now=now,
            )
        elif target_enum is DataDeletionTarget.OBSERVATION:
            outcome = await self._redact_observation(
                organization_id=org,
                observation_id=target_id,
                accepted_by=accepted_by,
                reason=reason,
                actor=actor,
                actor_role=actor_role,
                now=now,
            )
        else:
            raise BackupRestoreError(
                f"RETENTION_INVALID:target_unsupported:{target_value}"
            )
        return outcome

    async def _anonymize_lead(
        self,
        *,
        organization_id: str,
        lead_id: str,
        accepted_by: str,
        reason: str,
        actor: str,
        actor_role: str,
        now: datetime,
    ) -> dict[str, Any]:
        r = await self._session.execute(
            select(LeadRow).where(
                LeadRow.organization_id == organization_id,
                LeadRow.id == lead_id,
            )
        )
        row = r.scalar_one_or_none()
        if row is None:
            raise BackupRestoreError(
                f"LEAD_NOT_FOUND:lead_id:{lead_id}"
            )
        if getattr(row, "anonymized_at", None) is not None:
            raise BackupRestoreError(
                f"LEAD_ALREADY_ANONYMIZED:lead_id:{lead_id}"
            )
        # The bounded path marks the lead as
        # anonymized and removes the public profile
        # URL. Display name and company name are
        # preserved for audit linkage.
        row.anonymized_at = now
        row.anonymized_by = accepted_by
        row.public_url = None
        await self._session.flush()
        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role, actor_id=actor or None),
            action=AuditAction.DATA_LEAD_DELETED,
            target=AuditTarget(
                target_type=AuditTargetType.LEAD,
                target_id=lead_id,
                display=f"lead:{lead_id}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="data.lead.delete"),
            metadata=_safe_metadata(
                {
                    "lead_id": lead_id,
                    "accepted_by": accepted_by,
                    "reason": reason,
                    "anonymized_at": now.isoformat(),
                }
            ),
        )
        return {
            "target": DataDeletionTarget.LEAD.value,
            "target_id": lead_id,
            "status": "anonymized",
            "anonymized_at": now.isoformat(),
        }

    async def _disable_user(
        self,
        *,
        organization_id: str,
        user_id: str,
        accepted_by: str,
        reason: str,
        actor: str,
        actor_role: str,
        now: datetime,
    ) -> dict[str, Any]:
        r = await self._session.execute(
            select(UserRow).where(UserRow.id == user_id)
        )
        row = r.scalar_one_or_none()
        if row is None:
            raise BackupRestoreError(
                f"USER_NOT_FOUND:user_id:{user_id}"
            )
        if getattr(row, "disabled_at", None) is not None:
            raise BackupRestoreError(
                f"USER_ALREADY_DISABLED:user_id:{user_id}"
            )
        row.disabled_at = now
        row.disabled_by = accepted_by
        row.email = None
        row.disabled = True
        await self._session.flush()
        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role, actor_id=actor or None),
            action=AuditAction.DATA_USER_DELETED,
            target=AuditTarget(
                target_type=AuditTargetType.USER,
                target_id=user_id,
                display=f"user:{user_id}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="data.user.delete"),
            metadata=_safe_metadata(
                {
                    "user_id": user_id,
                    "accepted_by": accepted_by,
                    "reason": reason,
                    "disabled_at": now.isoformat(),
                }
            ),
        )
        return {
            "target": DataDeletionTarget.USER.value,
            "target_id": user_id,
            "status": "disabled",
            "disabled_at": now.isoformat(),
        }

    async def _redact_observation(
        self,
        *,
        organization_id: str,
        observation_id: str,
        accepted_by: str,
        reason: str,
        actor: str,
        actor_role: str,
        now: datetime,
    ) -> dict[str, Any]:
        r = await self._session.execute(
            select(EventSourceObservationRow).where(
                EventSourceObservationRow.id == observation_id,
            )
        )
        row = r.scalar_one_or_none()
        if row is None:
            raise BackupRestoreError(
                f"OBSERVATION_NOT_FOUND:observation_id:{observation_id}"
            )
        if getattr(row, "redacted_at", None) is not None:
            raise BackupRestoreError(
                f"OBSERVATION_ALREADY_REDACTED:observation_id:{observation_id}"
            )
        row.redacted_at = now
        row.redacted_by = accepted_by
        await self._session.flush()
        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role, actor_id=actor or None),
            action=AuditAction.DATA_OBSERVATION_DELETED,
            target=AuditTarget(
                target_type=AuditTargetType.SOURCE_OBSERVATION,
                target_id=observation_id,
                display=f"observation:{observation_id}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="data.observation.delete"),
            metadata=_safe_metadata(
                {
                    "observation_id": observation_id,
                    "accepted_by": accepted_by,
                    "reason": reason,
                    "redacted_at": now.isoformat(),
                }
            ),
        )
        return {
            "target": DataDeletionTarget.OBSERVATION.value,
            "target_id": observation_id,
            "status": "redacted",
            "redacted_at": now.isoformat(),
        }


__all__ = ["DataDeletionService"]
