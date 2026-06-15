"""Source-scoped CloakBrowser approval, runtime policy, and kill-switch rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class CloakBrowserPolicyState(StrEnum):
    DISABLED = "disabled"
    REQUESTED = "requested"
    PENDING = "pending"
    APPROVED = "approved"
    REVOKED = "revoked"
    BLOCKED = "blocked"
    RUNTIME_FAILED = "runtime_failed"


class CloakBrowserRuntimeStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    OK = "ok"
    KILL_SWITCH = "kill_switch"
    VERSION_UNPINNED = "version_unpinned"
    VERSION_MISMATCH = "version_mismatch"
    CHECKSUM_FAILED = "checksum_failed"
    CHECKSUM_MISSING = "checksum_missing"


class CloakBrowserBlockedReason(StrEnum):
    NOT_REQUESTED = "cloakbrowser_not_enabled"
    PENDING_APPROVAL = "cloakbrowser_pending_approval"
    UNAPPROVED = "cloakbrowser_unapproved"
    REVOKED = "cloakbrowser_revoked"
    KILL_SWITCH = "cloakbrowser_kill_switch"
    RUNTIME_POLICY = "cloakbrowser_runtime_policy_failed"
    ENGINE_NOT_CLOAK = "cloakbrowser_engine_not_selected"


@dataclass(frozen=True, slots=True)
class CloakBrowserRuntimePolicyInput:
    kill_switch_active: bool = False
    pinned_version: str | None = None
    runtime_version: str | None = None
    expected_checksum: str | None = None
    runtime_checksum: str | None = None
    require_checksum_when_configured: bool = True


@dataclass(frozen=True, slots=True)
class CloakBrowserPolicySnapshot:
    source_id: UUID
    organization_id: UUID
    state: CloakBrowserPolicyState
    purpose_rationale: str
    owner_admin_approved: bool
    compliance_approved: bool
    owner_admin_actor: str | None
    compliance_actor: str | None
    owner_admin_approved_at: datetime | None
    compliance_approved_at: datetime | None
    revoked_at: datetime | None
    revoked_by: str | None
    revoke_reason: str | None
    pinned_version: str | None
    runtime_status: CloakBrowserRuntimeStatus
    updated_at: datetime | None = None

    @property
    def fully_approved(self) -> bool:
        return (
            self.state == CloakBrowserPolicyState.APPROVED
            and self.owner_admin_approved
            and self.compliance_approved
            and self.revoked_at is None
        )


def is_cloakbrowser_engine_requested(automation_engine: str | None) -> bool:
    raw = (automation_engine or "").lower()
    return raw in ("cloakbrowser", "cloak")


def evaluate_runtime_policy(inp: CloakBrowserRuntimePolicyInput) -> CloakBrowserRuntimeStatus:
    if inp.kill_switch_active:
        return CloakBrowserRuntimeStatus.KILL_SWITCH
    if inp.pinned_version and not str(inp.pinned_version).strip():
        return CloakBrowserRuntimeStatus.VERSION_UNPINNED
    if inp.pinned_version and inp.runtime_version:
        if inp.pinned_version.strip() != inp.runtime_version.strip():
            return CloakBrowserRuntimeStatus.VERSION_MISMATCH
    if inp.expected_checksum:
        if not inp.runtime_checksum:
            return CloakBrowserRuntimeStatus.CHECKSUM_MISSING
        if inp.runtime_checksum.strip().lower() != inp.expected_checksum.strip().lower():
            return CloakBrowserRuntimeStatus.CHECKSUM_FAILED
    return CloakBrowserRuntimeStatus.OK


def map_blocked_reasons(
    *,
    engine_requested: bool,
    snapshot: CloakBrowserPolicySnapshot | None,
    runtime: CloakBrowserRuntimeStatus,
) -> tuple[str, ...]:
    if not engine_requested:
        return (CloakBrowserBlockedReason.ENGINE_NOT_CLOAK.value,)
    if snapshot is None or snapshot.state == CloakBrowserPolicyState.DISABLED:
        return (CloakBrowserBlockedReason.NOT_REQUESTED.value,)
    if snapshot.state == CloakBrowserPolicyState.REVOKED or snapshot.revoked_at:
        return (CloakBrowserBlockedReason.REVOKED.value,)
    if runtime == CloakBrowserRuntimeStatus.KILL_SWITCH:
        return (CloakBrowserBlockedReason.KILL_SWITCH.value,)
    if runtime not in (CloakBrowserRuntimeStatus.OK, CloakBrowserRuntimeStatus.NOT_APPLICABLE):
        return (CloakBrowserBlockedReason.RUNTIME_POLICY.value, runtime.value)
    if snapshot.state in (CloakBrowserPolicyState.REQUESTED, CloakBrowserPolicyState.PENDING):
        return (CloakBrowserBlockedReason.PENDING_APPROVAL.value,)
    if not snapshot.fully_approved:
        return (CloakBrowserBlockedReason.UNAPPROVED.value,)
    return ()


def derive_policy_state(
    *,
    requested: bool,
    owner_admin_approved: bool,
    compliance_approved: bool,
    revoked_at: datetime | None,
    runtime_status: CloakBrowserRuntimeStatus,
) -> CloakBrowserPolicyState:
    if revoked_at is not None:
        return CloakBrowserPolicyState.REVOKED
    if not requested:
        return CloakBrowserPolicyState.DISABLED
    if runtime_status not in (
        CloakBrowserRuntimeStatus.OK,
        CloakBrowserRuntimeStatus.NOT_APPLICABLE,
    ):
        return CloakBrowserPolicyState.RUNTIME_FAILED
    if owner_admin_approved and compliance_approved:
        return CloakBrowserPolicyState.APPROVED
    if requested:
        return CloakBrowserPolicyState.PENDING
    return CloakBrowserPolicyState.REQUESTED


def evaluate_cloakbrowser_launch(
    *,
    automation_engine: str | None,
    snapshot: CloakBrowserPolicySnapshot | None,
    runtime_input: CloakBrowserRuntimePolicyInput,
) -> tuple[bool, tuple[str, ...], CloakBrowserRuntimeStatus]:
    """Return (allowed, blocked_reasons, runtime_status)."""
    if not is_cloakbrowser_engine_requested(automation_engine):
        return True, (), CloakBrowserRuntimeStatus.NOT_APPLICABLE
    runtime = evaluate_runtime_policy(runtime_input)
    reasons = map_blocked_reasons(
        engine_requested=True,
        snapshot=snapshot,
        runtime=runtime,
    )
    if reasons:
        return False, reasons, runtime
    return True, (), runtime