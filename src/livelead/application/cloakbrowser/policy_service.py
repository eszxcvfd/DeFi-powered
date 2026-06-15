"""CloakBrowser governance application service (US-025)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.cloakbrowser.policy import (
    CloakBrowserPolicySnapshot,
    CloakBrowserPolicyState,
    CloakBrowserRuntimePolicyInput,
    CloakBrowserRuntimeStatus,
    derive_policy_state,
    evaluate_cloakbrowser_launch,
    evaluate_runtime_policy,
)
from livelead.infrastructure.db.models import CloakBrowserPolicyRow
from livelead.infrastructure.db.repositories.cloakbrowser_policies import CloakBrowserPolicyRepository
from livelead.infrastructure.db.repositories.sources import SourceRepository
from livelead.infrastructure.db.source_mappers import row_to_source
from livelead.runtime.settings import AppSettings

logger = logging.getLogger("livelead.cloakbrowser_policy")

COMPLIANCE_ROLES = frozenset({"compliance", "admin", "owner"})
OWNER_ADMIN_ROLES = frozenset({"admin", "owner"})


@dataclass(frozen=True, slots=True)
class CloakBrowserPolicyBlocked(Exception):
    reasons: tuple[str, ...]


def _row_to_snapshot(row: CloakBrowserPolicyRow, runtime_status: CloakBrowserRuntimeStatus) -> CloakBrowserPolicySnapshot:
    requested = bool(row.purpose_rationale.strip()) or row.owner_admin_approved or row.compliance_approved
    state = derive_policy_state(
        requested=requested,
        owner_admin_approved=bool(row.owner_admin_approved),
        compliance_approved=bool(row.compliance_approved),
        revoked_at=row.revoked_at,
        runtime_status=runtime_status,
    )
    return CloakBrowserPolicySnapshot(
        source_id=UUID(row.source_id),
        organization_id=UUID(row.organization_id),
        state=state,
        purpose_rationale=row.purpose_rationale or "",
        owner_admin_approved=bool(row.owner_admin_approved),
        compliance_approved=bool(row.compliance_approved),
        owner_admin_actor=row.owner_admin_actor,
        compliance_actor=row.compliance_actor,
        owner_admin_approved_at=row.owner_admin_approved_at,
        compliance_approved_at=row.compliance_approved_at,
        revoked_at=row.revoked_at,
        revoked_by=row.revoked_by,
        revoke_reason=row.revoke_reason,
        pinned_version=row.pinned_version,
        runtime_status=runtime_status,
        updated_at=row.updated_at,
    )


def runtime_input_from_settings(settings: AppSettings) -> CloakBrowserRuntimePolicyInput:
    return CloakBrowserRuntimePolicyInput(
        kill_switch_active=settings.cloakbrowser_kill_switch,
        pinned_version=settings.cloakbrowser_pinned_version,
        runtime_version=settings.cloakbrowser_runtime_version,
        expected_checksum=settings.cloakbrowser_expected_checksum,
        runtime_checksum=settings.cloakbrowser_runtime_checksum,
    )


class CloakBrowserPolicyService:
    def __init__(self, session: AsyncSession, settings: AppSettings) -> None:
        self._session = session
        self._settings = settings
        self._repo = CloakBrowserPolicyRepository(session)
        self._sources = SourceRepository(session)

    def _runtime_input_for_row(self, row: CloakBrowserPolicyRow | None) -> CloakBrowserRuntimePolicyInput:
        inp = runtime_input_from_settings(self._settings)
        if row and row.pinned_version:
            return CloakBrowserRuntimePolicyInput(
                kill_switch_active=inp.kill_switch_active,
                pinned_version=row.pinned_version,
                runtime_version=inp.runtime_version,
                expected_checksum=row.expected_checksum or inp.expected_checksum,
                runtime_checksum=inp.runtime_checksum,
            )
        return inp

    def _runtime_status_for_row(self, row: CloakBrowserPolicyRow | None) -> CloakBrowserRuntimeStatus:
        return evaluate_runtime_policy(self._runtime_input_for_row(row))

    async def get_view(self, source_id: UUID, organization_id: UUID) -> dict | None:
        src_row = await self._sources.get(source_id, organization_id)
        if not src_row:
            return None
        source = row_to_source(src_row)
        row = await self._repo.get_for_source(source_id, organization_id)
        runtime = self._runtime_status_for_row(row)
        snapshot = _row_to_snapshot(row, runtime) if row else None
        runtime_inp = self._runtime_input_for_row(row)
        allowed, reasons, _ = evaluate_cloakbrowser_launch(
            automation_engine=source.automation_engine,
            snapshot=snapshot,
            runtime_input=runtime_inp,
        )
        view = self._public_view(source, row, snapshot, allowed, reasons)
        view["kill_switch_active"] = bool(self._settings.cloakbrowser_kill_switch)
        return view

    @staticmethod
    def _public_view(source, row, snapshot, allowed: bool, reasons: tuple[str, ...]) -> dict:
        state = snapshot.state.value if snapshot else CloakBrowserPolicyState.DISABLED.value
        return {
            "source_id": str(source.id),
            "source_name": source.name,
            "automation_engine": source.automation_engine,
            "policy_state": state,
            "purpose_rationale": snapshot.purpose_rationale if snapshot else "",
            "owner_admin_approved": snapshot.owner_admin_approved if snapshot else False,
            "compliance_approved": snapshot.compliance_approved if snapshot else False,
            "owner_admin_actor": snapshot.owner_admin_actor if snapshot else None,
            "compliance_actor": snapshot.compliance_actor if snapshot else None,
            "owner_admin_approved_at": _iso(snapshot.owner_admin_approved_at) if snapshot else None,
            "compliance_approved_at": _iso(snapshot.compliance_approved_at) if snapshot else None,
            "revoked_at": _iso(snapshot.revoked_at) if snapshot else None,
            "revoked_by": snapshot.revoked_by if snapshot else None,
            "revoke_reason": snapshot.revoke_reason if snapshot else None,
            "pinned_version": snapshot.pinned_version if snapshot else None,
            "runtime_status": snapshot.runtime_status.value if snapshot else CloakBrowserRuntimeStatus.NOT_APPLICABLE.value,
            "kill_switch_active": False,  # caller may override from settings
            "cloakbrowser_launch_allowed": allowed,
            "blocked_reasons": list(reasons),
            "has_policy_record": row is not None,
        }

    async def request_enablement(
        self,
        organization_id: UUID,
        source_id: UUID,
        actor: str,
        *,
        purpose_rationale: str,
        pinned_version: str | None = None,
        expected_checksum: str | None = None,
    ) -> dict:
        src_row = await self._sources.get(source_id, organization_id)
        if not src_row:
            raise LookupError("source_not_found")
        row = await self._repo.upsert_request(
            organization_id=organization_id,
            source_id=source_id,
            actor=actor,
            purpose_rationale=purpose_rationale,
            pinned_version=pinned_version,
            expected_checksum=expected_checksum,
        )
        logger.info("cloakbrowser request source=%s actor=%s", source_id, actor)
        view = await self.get_view(source_id, organization_id)
        assert view is not None
        return view

    async def approve_owner_admin(self, organization_id: UUID, source_id: UUID, actor: str) -> dict:
        if actor not in OWNER_ADMIN_ROLES:
            raise PermissionError("owner_admin_role_required")
        row = await self._require_policy_row(source_id, organization_id)
        await self._repo.apply_owner_admin_approval(row, actor)
        logger.info("cloakbrowser owner_admin_approved source=%s actor=%s", source_id, actor)
        view = await self.get_view(source_id, organization_id)
        assert view is not None
        return view

    async def approve_compliance(self, organization_id: UUID, source_id: UUID, actor: str) -> dict:
        if actor not in COMPLIANCE_ROLES:
            raise PermissionError("compliance_role_required")
        row = await self._require_policy_row(source_id, organization_id)
        await self._repo.apply_compliance_approval(row, actor)
        logger.info("cloakbrowser compliance_approved source=%s actor=%s", source_id, actor)
        view = await self.get_view(source_id, organization_id)
        assert view is not None
        return view

    async def revoke(self, organization_id: UUID, source_id: UUID, actor: str, *, reason: str) -> dict:
        if actor not in OWNER_ADMIN_ROLES:
            raise PermissionError("owner_admin_role_required")
        row = await self._require_policy_row(source_id, organization_id)
        await self._repo.revoke(row, actor=actor, reason=reason)
        logger.info("cloakbrowser revoked source=%s actor=%s", source_id, actor)
        view = await self.get_view(source_id, organization_id)
        assert view is not None
        return view

    async def assert_launch_allowed(
        self,
        organization_id: UUID,
        source_id: UUID,
        automation_engine: str | None,
    ) -> None:
        row = await self._repo.get_for_source(source_id, organization_id)
        runtime = self._runtime_status_for_row(row)
        snapshot = _row_to_snapshot(row, runtime) if row else None
        allowed, reasons, _ = evaluate_cloakbrowser_launch(
            automation_engine=automation_engine,
            snapshot=snapshot,
            runtime_input=self._runtime_input_for_row(row),
        )
        if not allowed:
            raise CloakBrowserPolicyBlocked(reasons)

    async def _require_policy_row(self, source_id: UUID, organization_id: UUID) -> CloakBrowserPolicyRow:
        row = await self._repo.get_for_source(source_id, organization_id)
        if not row:
            raise LookupError("cloakbrowser_policy_not_found")
        return row


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None