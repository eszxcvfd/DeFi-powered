"""Browser profile application service (US-024)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.browser.profiles import (
    BrowserProfileConsentStatus,
    BrowserProfileLifecycle,
    can_store_state_material,
    can_transition_delete,
    can_transition_expire,
    can_transition_lock,
    can_transition_renew,
    effective_lifecycle,
    evaluate_profile_launch,
    profile_boundary,
    profile_isolation_key,
    secret_safe_summary,
)
from livelead.infrastructure.db.models import BrowserProfileRow
from livelead.infrastructure.db.repositories.browser_profiles import BrowserProfileRepository
from livelead.infrastructure.secrets.vault import SecretVault

logger = logging.getLogger("livelead.browser_profile")


@dataclass(frozen=True, slots=True)
class ProfileBlocked(Exception):
    reasons: tuple[str, ...]


class BrowserProfileService:
    def __init__(self, session: AsyncSession, vault: SecretVault) -> None:
        self._session = session
        self._repo = BrowserProfileRepository(session)
        self._vault = vault

    async def create(
        self,
        organization_id: UUID,
        actor: str,
        *,
        name: str,
        ttl_days: int | None = 30,
    ) -> BrowserProfileRow:
        expires = None
        if ttl_days and ttl_days > 0:
            expires = datetime.now(UTC) + timedelta(days=ttl_days)
        row = BrowserProfileRepository.new_row(
            organization_id=organization_id,
            name=name,
            created_by=actor,
            expires_at=expires,
        )
        await self._repo.add(row)
        logger.info(
            "browser_profile created id=%s org=%s actor=%s",
            row.id,
            organization_id,
            actor,
        )
        return row

    async def list_profiles(self, organization_id: UUID) -> list[dict]:
        rows = await self._repo.list_for_organization(organization_id)
        return [self._to_view(r) for r in rows]

    async def get_profile(self, profile_id: UUID, organization_id: UUID) -> dict | None:
        row = await self._repo.get(profile_id, organization_id)
        if not row:
            return None
        return self._to_view(row)

    async def lock(self, profile_id: UUID, organization_id: UUID, actor: str) -> dict:
        row = await self._require_mutable(profile_id, organization_id)
        state = BrowserProfileLifecycle(row.lifecycle_state)
        if not can_transition_lock(state):
            raise ValueError("profile_not_lockable")
        row.lifecycle_state = BrowserProfileLifecycle.LOCKED.value
        row.locked_at = datetime.now(UTC)
        row.updated_at = datetime.now(UTC)
        logger.info("browser_profile locked id=%s actor=%s", profile_id, actor)
        return self._to_view(row)

    async def renew(
        self,
        profile_id: UUID,
        organization_id: UUID,
        actor: str,
        *,
        ttl_days: int = 30,
    ) -> dict:
        row = await self._require_mutable(profile_id, organization_id)
        state = BrowserProfileLifecycle(row.lifecycle_state)
        if state == BrowserProfileLifecycle.DELETED:
            raise ValueError("profile_not_renewable")
        if state not in (
            BrowserProfileLifecycle.ACTIVE,
            BrowserProfileLifecycle.EXPIRED,
            BrowserProfileLifecycle.PENDING_RENEWAL,
            BrowserProfileLifecycle.LOCKED,
        ):
            raise ValueError("profile_not_renewable")
        row.lifecycle_state = BrowserProfileLifecycle.ACTIVE.value
        row.locked_at = None
        row.expires_at = datetime.now(UTC) + timedelta(days=max(1, ttl_days))
        row.updated_at = datetime.now(UTC)
        logger.info("browser_profile renewed id=%s actor=%s", profile_id, actor)
        return self._to_view(row)

    async def expire(self, profile_id: UUID, organization_id: UUID, actor: str) -> dict:
        row = await self._require_mutable(profile_id, organization_id)
        state = BrowserProfileLifecycle(row.lifecycle_state)
        if not can_transition_expire(state) and state != BrowserProfileLifecycle.ACTIVE:
            raise ValueError("profile_not_expirable")
        row.lifecycle_state = BrowserProfileLifecycle.EXPIRED.value
        row.expires_at = datetime.now(UTC)
        row.updated_at = datetime.now(UTC)
        logger.info("browser_profile expired id=%s actor=%s", profile_id, actor)
        return self._to_view(row)

    async def delete(self, profile_id: UUID, organization_id: UUID, actor: str) -> dict:
        row = await self._repo.get(profile_id, organization_id)
        if not row:
            raise LookupError("profile not found")
        state = BrowserProfileLifecycle(row.lifecycle_state)
        if not can_transition_delete(state):
            raise ValueError("profile_already_deleted")
        row.lifecycle_state = BrowserProfileLifecycle.DELETED.value
        row.deleted_at = datetime.now(UTC)
        row.state_material_ciphertext = None
        row.consent_status = BrowserProfileConsentStatus.REVOKED.value
        row.updated_at = datetime.now(UTC)
        logger.info("browser_profile deleted id=%s actor=%s", profile_id, actor)
        return self._to_view(row)

    async def record_consent(
        self,
        profile_id: UUID,
        organization_id: UUID,
        actor: str,
        *,
        granted: bool,
    ) -> dict:
        row = await self._require_mutable(profile_id, organization_id)
        row.consent_status = (
            BrowserProfileConsentStatus.GRANTED.value
            if granted
            else BrowserProfileConsentStatus.REVOKED.value
        )
        row.consent_recorded_at = datetime.now(UTC)
        row.consent_actor = actor
        row.updated_at = datetime.now(UTC)
        if not granted:
            row.state_material_ciphertext = None
        logger.info(
            "browser_profile consent id=%s granted=%s actor=%s",
            profile_id,
            granted,
            actor,
        )
        return self._to_view(row)

    async def store_state_material(
        self,
        profile_id: UUID,
        organization_id: UUID,
        actor: str,
        *,
        payload: dict,
    ) -> dict:
        row = await self._require_mutable(profile_id, organization_id)
        consent = BrowserProfileConsentStatus(row.consent_status)
        lifecycle = BrowserProfileLifecycle(row.lifecycle_state)
        ok, reason = can_store_state_material(consent_status=consent, lifecycle=lifecycle)
        if not ok:
            raise ValueError(reason or "store_denied")
        ciphertext = self._vault.encrypt(json.dumps(payload, separators=(",", ":")))
        row.state_material_ciphertext = ciphertext
        row.updated_at = datetime.now(UTC)
        logger.info("browser_profile state_stored id=%s actor=%s", profile_id, actor)
        return self._to_view(row)

    async def assert_launch_eligible(
        self, profile_id: UUID, organization_id: UUID
    ) -> tuple[BrowserProfileRow, str, str]:
        row = await self._repo.get(profile_id, organization_id)
        if not row:
            raise LookupError("profile not found")
        lifecycle = BrowserProfileLifecycle(row.lifecycle_state)
        consent = BrowserProfileConsentStatus(row.consent_status)
        has_mat = bool(row.state_material_ciphertext)
        elig = evaluate_profile_launch(
            lifecycle=lifecycle,
            expires_at=row.expires_at,
            consent_status=consent,
            has_state_material=has_mat,
        )
        if not elig.eligible:
            raise ProfileBlocked(elig.reasons)
        org = str(organization_id)
        return row, profile_isolation_key(org, row.id), profile_boundary(org, row.id)

    async def touch_last_used(self, profile_id: UUID, organization_id: UUID) -> None:
        row = await self._repo.get(profile_id, organization_id)
        if row:
            row.last_used_at = datetime.now(UTC)
            row.updated_at = datetime.now(UTC)

    def load_storage_state_for_runtime(self, row: BrowserProfileRow) -> dict | None:
        if not row.state_material_ciphertext:
            return None
        try:
            raw = self._vault.decrypt(row.state_material_ciphertext)
            return json.loads(raw)
        except (ValueError, json.JSONDecodeError):
            logger.warning("browser_profile state_decrypt_failed id=%s", row.id)
            return None

    async def _require_mutable(self, profile_id: UUID, organization_id: UUID) -> BrowserProfileRow:
        row = await self._repo.get(profile_id, organization_id)
        if not row:
            raise LookupError("profile not found")
        if row.lifecycle_state in (
            BrowserProfileLifecycle.DELETED.value,
            BrowserProfileLifecycle.DELETING.value,
        ):
            raise ValueError("profile_terminal")
        return row

    def _to_view(self, row: BrowserProfileRow) -> dict:
        stored = BrowserProfileLifecycle(row.lifecycle_state)
        consent = BrowserProfileConsentStatus(row.consent_status)
        has_mat = bool(row.state_material_ciphertext)
        effective = effective_lifecycle(stored, expires_at=row.expires_at)
        launch = evaluate_profile_launch(
            lifecycle=stored,
            expires_at=row.expires_at,
            consent_status=consent,
            has_state_material=has_mat,
        )
        safe = secret_safe_summary(has_state_material=has_mat, consent_status=consent)
        return {
            "id": row.id,
            "name": row.name,
            "lifecycle_state": stored.value,
            "effective_state": effective.value,
            "launch_eligible": launch.eligible,
            "launch_blocked_reasons": list(launch.reasons),
            "created_by": row.created_by,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "locked_at": row.locked_at.isoformat() if row.locked_at else None,
            "deleted_at": row.deleted_at.isoformat() if row.deleted_at else None,
            "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
            "consent_status": consent.value,
            "consent_recorded_at": row.consent_recorded_at.isoformat()
            if row.consent_recorded_at
            else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            **safe,
        }


def is_expired_row(row: BrowserProfileRow) -> bool:
    return effective_lifecycle(
        BrowserProfileLifecycle(row.lifecycle_state),
        expires_at=row.expires_at,
    ) == BrowserProfileLifecycle.EXPIRED