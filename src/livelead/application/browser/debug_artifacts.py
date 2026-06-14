"""Browser debug artifact orchestration (US-023)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.browser.debug_artifacts import (
    BrowserArtifactCaptureMode,
    BrowserArtifactStatus,
    BrowserArtifactType,
    can_access_artifact,
    effective_artifact_status,
    can_capture_screenshot,
    can_enable_debug,
    parse_browser_artifact_policy,
    retention_expires_at,
    sanitize_text_payload,
)
from livelead.domain.browser.models import BrowserSessionState
from livelead.infrastructure.browser.adapter import capture_session_screenshot
from livelead.infrastructure.browser.artifact_store import artifact_root, read_blob, relative_storage_key, write_blob
from livelead.infrastructure.db.repositories.browser_debug_artifacts import BrowserDebugArtifactRepository
from livelead.infrastructure.db.repositories.browser_sessions import BrowserSessionRepository
from livelead.infrastructure.db.repositories.sources import SourceRepository
from livelead.runtime.settings import AppSettings

logger = logging.getLogger("livelead.browser_artifacts")


class BrowserDebugArtifactService:
    def __init__(self, session: AsyncSession, settings: AppSettings) -> None:
        self._session = session
        self._settings = settings
        self._sessions = BrowserSessionRepository(session)
        self._sources = SourceRepository(session)
        self._artifacts = BrowserDebugArtifactRepository(session)

    async def set_debug_enabled(
        self,
        session_id: UUID,
        organization_id: UUID,
        actor_role: str,
        *,
        enabled: bool,
    ) -> dict:
        row = await self._sessions.get(session_id, organization_id)
        if not row:
            raise LookupError("session not found")
        src = await self._sources.get(UUID(row.source_id), organization_id)
        policy = parse_browser_artifact_policy(src.rate_limit_json if src else None)
        if enabled:
            decision = can_enable_debug(policy=policy, actor_role=actor_role)
            if not decision.allowed:
                return {"debug_enabled": False, "policy_reason": decision.reason}
        row.debug_enabled = bool(enabled)
        await self._session.flush()
        logger.info(
            "browser_debug_toggled session=%s enabled=%s actor=%s",
            session_id,
            enabled,
            actor_role,
        )
        if enabled:
            await self._maybe_capture_debug_artifacts(
                session_id, organization_id, actor_role, policy, row
            )
        return {"debug_enabled": row.debug_enabled}

    async def _maybe_capture_debug_artifacts(self, session_id, organization_id, actor, policy, row) -> None:
        if not row.debug_enabled:
            return
        console = "[info] debug session — supervised automation trace (stub)\n"
        sanitized, redacted = sanitize_text_payload(console)
        await self._persist_text_artifact(
            session_id=session_id,
            organization_id=organization_id,
            actor=actor,
            artifact_type=BrowserArtifactType.CONSOLE_LOG,
            capture_mode=BrowserArtifactCaptureMode.DEBUG_AUTO,
            text=sanitized,
            policy=policy,
            redacted=redacted,
            ext="log",
            content_type="text/plain; charset=utf-8",
            summary="Console log captured (debug enabled).",
        )
        trace = json.dumps({"version": 1, "engine": row.engine, "mode": "debug_stub"}, indent=2)
        await self._persist_text_artifact(
            session_id=session_id,
            organization_id=organization_id,
            actor=actor,
            artifact_type=BrowserArtifactType.TRACE,
            capture_mode=BrowserArtifactCaptureMode.DEBUG_AUTO,
            text=trace,
            policy=policy,
            redacted=False,
            ext="json",
            content_type="application/json",
            summary="Trace metadata captured (debug enabled).",
        )

    async def capture_screenshot(
        self,
        session_id: UUID,
        organization_id: UUID,
        actor: str,
    ) -> dict:
        row = await self._sessions.get(session_id, organization_id)
        if not row:
            raise LookupError("session not found")
        src = await self._sources.get(UUID(row.source_id), organization_id)
        policy = parse_browser_artifact_policy(src.rate_limit_json if src else None)
        decision = can_capture_screenshot(
            session_state=BrowserSessionState(row.status),
            policy=policy,
        )
        if not decision.allowed:
            return {
                "status": BrowserArtifactStatus.BLOCKED.value,
                "summary": "Screenshot capture not allowed.",
                "policy_reason": decision.reason,
            }
        png = capture_session_screenshot(session_id)
        if not png:
            return {
                "status": BrowserArtifactStatus.FAILED.value,
                "summary": "No active browser runtime for screenshot.",
            }
        base = self._settings.artifact_root
        art_row = await self._artifacts.add(
            BrowserDebugArtifactRepository.new_row(
                session_id=session_id,
                organization_id=organization_id,
                artifact_type=BrowserArtifactType.SCREENSHOT.value,
                capture_mode=BrowserArtifactCaptureMode.MANUAL.value,
                status=BrowserArtifactStatus.ACTIVE.value,
                storage_path="pending",
                content_type="image/png",
                byte_size=len(png),
                captured_by=actor,
                summary="Manual session screenshot.",
                expires_at=retention_expires_at(
                    artifact_type=BrowserArtifactType.SCREENSHOT,
                    policy=policy,
                ),
            )
        )
        path = write_blob(
            base,
            organization_id,
            session_id,
            UUID(art_row.id),
            png,
            "png",
        )
        art_row.storage_path = relative_storage_key(path, base)
        row.latest_artifact_summary = f"Screenshot captured ({art_row.id[:8]}…)"
        await self._session.flush()
        logger.info(
            "browser_artifact_screenshot session=%s artifact=%s actor=%s bytes=%s",
            session_id,
            art_row.id,
            actor,
            len(png),
        )
        return self._artifact_view(art_row)

    async def _persist_text_artifact(
        self,
        *,
        session_id: UUID,
        organization_id: UUID,
        actor: str,
        artifact_type: BrowserArtifactType,
        capture_mode: BrowserArtifactCaptureMode,
        text: str,
        policy: dict,
        redacted: bool,
        ext: str,
        content_type: str,
        summary: str,
    ) -> None:
        data = text.encode("utf-8")
        base = self._settings.artifact_root
        art_row = await self._artifacts.add(
            BrowserDebugArtifactRepository.new_row(
                session_id=session_id,
                organization_id=organization_id,
                artifact_type=artifact_type.value,
                capture_mode=capture_mode.value,
                status=BrowserArtifactStatus.ACTIVE.value,
                storage_path="pending",
                content_type=content_type,
                byte_size=len(data),
                captured_by=actor,
                summary=summary,
                expires_at=retention_expires_at(artifact_type=artifact_type, policy=policy),
                redacted=redacted,
            )
        )
        path = write_blob(base, organization_id, session_id, UUID(art_row.id), data, ext)
        art_row.storage_path = relative_storage_key(path, base)
        row = await self._sessions.get(session_id, organization_id)
        if row:
            row.latest_artifact_summary = summary
        await self._session.flush()

    async def list_artifacts(self, session_id: UUID, organization_id: UUID) -> list[dict]:
        rows = await self._artifacts.list_for_session(session_id, organization_id)
        return [self._artifact_view(r) for r in rows]

    async def read_artifact_bytes(
        self,
        artifact_id: UUID,
        organization_id: UUID,
        actor_role: str,
    ) -> tuple[bytes, str, str]:
        row = await self._artifacts.get(artifact_id, organization_id)
        if not row:
            raise LookupError("artifact not found")
        stored = BrowserArtifactStatus(row.status)
        effective = effective_artifact_status(stored, expires_at=row.expires_at)
        if effective == BrowserArtifactStatus.EXPIRED and row.status == BrowserArtifactStatus.ACTIVE.value:
            row.status = BrowserArtifactStatus.EXPIRED.value
            await self._session.flush()
        decision = can_access_artifact(
            status=effective,
            expires_at=row.expires_at,
            organization_id=str(organization_id),
            artifact_org_id=row.organization_id,
            actor_role=actor_role,
        )
        if not decision.allowed:
            raise PermissionError(decision.reason or "access denied")
        base = artifact_root(self._settings.artifact_root)
        path = base / row.storage_path
        if not path.is_file():
            raise FileNotFoundError("artifact blob missing")
        logger.info(
            "browser_artifact_access artifact=%s actor=%s type=%s",
            artifact_id,
            actor_role,
            row.artifact_type,
        )
        return read_blob(path), row.content_type, row.artifact_type

    @staticmethod
    def _artifact_view(row) -> dict:
        return {
            "id": row.id,
            "session_id": row.session_id,
            "artifact_type": row.artifact_type,
            "capture_mode": row.capture_mode,
            "status": row.status,
            "content_type": row.content_type,
            "byte_size": row.byte_size,
            "captured_by": row.captured_by,
            "summary": row.summary,
            "redacted": bool(row.redacted),
            "expires_at": row.expires_at.isoformat(),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }