"""Stub runtime for CI/tests — no network (legacy US-020 proof path)."""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from livelead.domain.browser.actions import BrowserActionType
from livelead.domain.browser.models import BrowserEngine, BrowserSessionState

logger = logging.getLogger("livelead.browser_stub")

_lock = threading.Lock()
_sessions: dict[str, _Runtime] = {}


@dataclass
class _Runtime:
    session_id: str
    organization_id: str
    engine: BrowserEngine
    state: BrowserSessionState
    current_url: str
    latest_action_summary: str
    started_at: datetime | None
    ended_at: datetime | None
    worker_id: str
    stop_requested: bool = False
    error_summary: str | None = None


def _worker_id() -> str:
    return f"browser-worker-stub-{os.getpid()}"


def _key(session_id: UUID) -> str:
    return str(session_id)


class StubBrowserRuntime:
    def schedule_session_start(
        self,
        *,
        session_id: UUID,
        organization_id: UUID,
        engine: BrowserEngine,
        initial_url: str,
        isolation_key: str,
        storage_state: dict | None = None,
    ) -> None:
        _ = isolation_key
        _ = storage_state

        def _run() -> None:
            import time

            key = _key(session_id)
            with _lock:
                rt = _sessions.get(key)
                if not rt or rt.stop_requested:
                    return
                rt.state = BrowserSessionState.STARTING
            time.sleep(0.05)
            with _lock:
                rt = _sessions.get(key)
                if not rt:
                    return
                if rt.stop_requested:
                    rt.state = BrowserSessionState.STOPPED
                    rt.ended_at = datetime.now(UTC)
                    rt.latest_action_summary = "Stopped before start completed"
                    return
                rt.state = BrowserSessionState.RUNNING
                rt.started_at = datetime.now(UTC)
                rt.current_url = initial_url
                rt.latest_action_summary = (
                    "Stub session (set LIVELEAD_BROWSER_AUTOMATION=playwright for real browser)"
                )
                logger.info("browser.session_started session=%s mode=stub", session_id)

        with _lock:
            _sessions[_key(session_id)] = _Runtime(
                session_id=str(session_id),
                organization_id=str(organization_id),
                engine=engine,
                state=BrowserSessionState.QUEUED,
                current_url="",
                latest_action_summary="Session queued (stub)",
                started_at=None,
                ended_at=None,
                worker_id=_worker_id(),
            )
        threading.Thread(target=_run, daemon=True, name=f"browser-stub-{session_id}").start()

    def read_runtime(self, session_id: UUID) -> dict | None:
        with _lock:
            rt = _sessions.get(_key(session_id))
            if not rt:
                return None
            return _as_dict(rt)

    def request_stop(self, session_id: UUID) -> dict | None:
        with _lock:
            rt = _sessions.get(_key(session_id))
            if not rt:
                return None
            rt.stop_requested = True
            if rt.state in (
                BrowserSessionState.QUEUED,
                BrowserSessionState.STARTING,
                BrowserSessionState.RUNNING,
                BrowserSessionState.NEEDS_USER_ACTION,
            ):
                rt.state = BrowserSessionState.STOPPING
                rt.latest_action_summary = "Stop requested"
            elif rt.state != BrowserSessionState.STOPPING:
                return _as_dict(rt)

        import time

        time.sleep(0.08)
        with _lock:
            rt = _sessions.get(_key(session_id))
            if not rt:
                return None
            if rt.state == BrowserSessionState.STOPPING:
                rt.state = BrowserSessionState.STOPPED
                rt.ended_at = datetime.now(UTC)
                rt.latest_action_summary = "Session stopped (stub)"
            return _as_dict(rt)

    def execute_read_only_action(
        self,
        session_id: UUID,
        *,
        action_type: BrowserActionType,
        parameters: dict,
        timeout_ms: int,
        source_domain: str,
    ) -> dict | None:
        _ = timeout_ms, source_domain
        key = _key(session_id)
        with _lock:
            rt = _sessions.get(key)
            if not rt:
                return None
            if rt.state not in (
                BrowserSessionState.RUNNING,
                BrowserSessionState.NEEDS_USER_ACTION,
            ):
                return {
                    "lifecycle": "blocked",
                    "summary": "Session is not in a runnable state for actions.",
                    "policy_reason": "session_not_actionable",
                }
            if action_type == BrowserActionType.NAVIGATE and parameters.get("url"):
                rt.current_url = str(parameters["url"])
            rt.latest_action_summary = f"Stub {action_type.value} completed"
            return {
                "lifecycle": "completed",
                "summary": rt.latest_action_summary,
                "current_url": rt.current_url,
                "text_preview": "Stub read text sample."
                if action_type == BrowserActionType.READ_TEXT
                else None,
            }

    def execute_confirmation_gated_action(
        self,
        session_id: UUID,
        *,
        action_type: BrowserActionType,
        parameters: dict,
        timeout_ms: int,
        source_domain: str,
    ) -> dict | None:
        _ = timeout_ms, source_domain, parameters
        key = _key(session_id)
        with _lock:
            rt = _sessions.get(key)
            if not rt:
                return None
            if rt.state not in (
                BrowserSessionState.RUNNING,
                BrowserSessionState.NEEDS_USER_ACTION,
            ):
                return {
                    "lifecycle": "blocked",
                    "summary": "Session is not in a runnable state for actions.",
                    "policy_reason": "session_not_actionable",
                }
            rt.latest_action_summary = f"Stub {action_type.value} executed (dry-run submit)"
            return {
                "lifecycle": "completed",
                "summary": rt.latest_action_summary,
                "current_url": rt.current_url,
                "detail": "Dry-run: no external form was submitted.",
            }

    def capture_screenshot(self, session_id: UUID) -> bytes | None:
        key = _key(session_id)
        with _lock:
            if key not in _sessions:
                return None
        # Minimal valid 1x1 PNG
        return bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
        )

    def reset_for_tests(self) -> None:
        with _lock:
            _sessions.clear()


def _as_dict(rt: _Runtime) -> dict:
    return {
        "state": rt.state,
        "current_url": rt.current_url,
        "latest_action_summary": rt.latest_action_summary,
        "started_at": rt.started_at,
        "ended_at": rt.ended_at,
        "worker_id": rt.worker_id,
        "stop_requested": rt.stop_requested,
        "error_summary": rt.error_summary,
    }
