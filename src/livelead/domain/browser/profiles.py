"""Governed browser profile lifecycle (US-024)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class BrowserProfileLifecycle(StrEnum):
    ACTIVE = "active"
    LOCKED = "locked"
    EXPIRED = "expired"
    PENDING_RENEWAL = "pending_renewal"
    DELETING = "deleting"
    DELETED = "deleted"


class BrowserProfileConsentStatus(StrEnum):
    NONE = "none"
    GRANTED = "granted"
    REVOKED = "revoked"


TERMINAL_PROFILE = frozenset(
    {BrowserProfileLifecycle.DELETED, BrowserProfileLifecycle.DELETING}
)


@dataclass(frozen=True, slots=True)
class ProfileLaunchEligibility:
    eligible: bool
    reasons: tuple[str, ...]


def is_profile_expired(*, expires_at: datetime | None, now: datetime | None = None) -> bool:
    if not expires_at:
        return False
    ref = now or datetime.now(UTC)
    exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=UTC)
    return ref >= exp


def effective_lifecycle(
    stored: BrowserProfileLifecycle,
    *,
    expires_at: datetime | None,
    now: datetime | None = None,
) -> BrowserProfileLifecycle:
    if stored in TERMINAL_PROFILE:
        return stored
    if stored == BrowserProfileLifecycle.LOCKED:
        return BrowserProfileLifecycle.LOCKED
    if stored == BrowserProfileLifecycle.PENDING_RENEWAL:
        return BrowserProfileLifecycle.PENDING_RENEWAL
    if is_profile_expired(expires_at=expires_at, now=now):
        return BrowserProfileLifecycle.EXPIRED
    return stored


def evaluate_profile_launch(
    *,
    lifecycle: BrowserProfileLifecycle,
    expires_at: datetime | None,
    consent_status: BrowserProfileConsentStatus,
    has_state_material: bool,
    now: datetime | None = None,
) -> ProfileLaunchEligibility:
    effective = effective_lifecycle(lifecycle, expires_at=expires_at, now=now)
    reasons: list[str] = []
    if effective == BrowserProfileLifecycle.DELETED:
        reasons.append("profile_deleted")
    elif effective == BrowserProfileLifecycle.DELETING:
        reasons.append("profile_deleting")
    elif effective == BrowserProfileLifecycle.LOCKED:
        reasons.append("profile_locked")
    elif effective == BrowserProfileLifecycle.EXPIRED:
        reasons.append("profile_expired")
    elif effective == BrowserProfileLifecycle.PENDING_RENEWAL:
        reasons.append("profile_pending_renewal")
    if has_state_material and consent_status != BrowserProfileConsentStatus.GRANTED:
        reasons.append("profile_consent_required")
    if reasons:
        return ProfileLaunchEligibility(eligible=False, reasons=tuple(reasons))
    return ProfileLaunchEligibility(eligible=True, reasons=())


def can_transition_lock(from_state: BrowserProfileLifecycle) -> bool:
    return from_state == BrowserProfileLifecycle.ACTIVE


def can_transition_renew(from_state: BrowserProfileLifecycle) -> bool:
    return from_state in (
        BrowserProfileLifecycle.EXPIRED,
        BrowserProfileLifecycle.PENDING_RENEWAL,
        BrowserProfileLifecycle.LOCKED,
    )


def can_transition_expire(from_state: BrowserProfileLifecycle) -> bool:
    return from_state in (BrowserProfileLifecycle.ACTIVE, BrowserProfileLifecycle.PENDING_RENEWAL)


def can_transition_delete(from_state: BrowserProfileLifecycle) -> bool:
    return from_state not in (BrowserProfileLifecycle.DELETED, BrowserProfileLifecycle.DELETING)


def can_store_state_material(
    *,
    consent_status: BrowserProfileConsentStatus,
    lifecycle: BrowserProfileLifecycle,
) -> tuple[bool, str | None]:
    if lifecycle in TERMINAL_PROFILE or lifecycle == BrowserProfileLifecycle.LOCKED:
        return False, "profile_not_writable"
    if consent_status != BrowserProfileConsentStatus.GRANTED:
        return False, "consent_not_granted"
    return True, None


def profile_isolation_key(organization_id: str, profile_id: str) -> str:
    return f"{organization_id}:profile:{profile_id}"


def profile_boundary(organization_id: str, profile_id: str) -> str:
    return f"workspace/{organization_id}/profile/{profile_id}"


def secret_safe_summary(
    *,
    has_state_material: bool,
    consent_status: BrowserProfileConsentStatus,
) -> dict[str, str | bool]:
    return {
        "state_material_present": has_state_material,
        "consent_status": consent_status.value,
        "raw_state_exposed": False,
    }