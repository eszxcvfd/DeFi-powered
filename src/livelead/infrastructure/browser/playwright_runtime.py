"""Real supervised browser sessions via Playwright (isolated context per session)."""

from __future__ import annotations

import logging
import os
import queue
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from livelead.domain.browser.actions import BrowserActionType
from livelead.domain.browser.models import BrowserEngine, BrowserSessionState
from livelead.domain.browser.navigation import (
    NavigationOutcome,
    classify_http_status,
    classify_navigation_exception,
)
from livelead.infrastructure.browser.action_executor import run_playwright_action
from livelead.infrastructure.browser.chromium_path import require_chromium_executable
from livelead.runtime.settings import AppSettings, parse_settings

logger = logging.getLogger("livelead.browser_playwright")

_lock = threading.Lock()
_sessions: dict[str, _LiveSession] = {}


@dataclass
class _LiveSession:
    session_id: str
    organization_id: str
    engine: BrowserEngine
    isolation_key: str
    state: BrowserSessionState = BrowserSessionState.QUEUED
    current_url: str = ""
    latest_action_summary: str = "Session queued"
    started_at: datetime | None = None
    ended_at: datetime | None = None
    worker_id: str = ""
    stop_requested: bool = False
    error_summary: str | None = None
    # Playwright handles (sync API, touched only on worker thread)
    _playwright: object | None = field(default=None, repr=False)
    _browser: object | None = field(default=None, repr=False)
    _context: object | None = field(default=None, repr=False)
    _page: object | None = field(default=None, repr=False)
    _action_queue: queue.Queue = field(default_factory=queue.Queue, repr=False)


def _worker_id() -> str:
    return f"browser-worker-{os.getpid()}"


def _key(session_id: UUID) -> str:
    return str(session_id)


def _profile_dir(settings: AppSettings, isolation_key: str) -> Path:
    root = settings.browser_profile_root
    safe = isolation_key.replace(":", "_").replace("/", "_")
    path = root / safe
    path.mkdir(parents=True, exist_ok=True)
    return path


def _chromium_launch_kwargs(settings: AppSettings, engine: BrowserEngine) -> dict:
    exe = require_chromium_executable(settings, engine)
    return {
        "headless": settings.browser_headless,
        "executable_path": exe,
    }


class PlaywrightBrowserRuntime:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self._settings = settings or parse_settings()

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
        with _lock:
            _sessions[_key(session_id)] = _LiveSession(
                session_id=str(session_id),
                organization_id=str(organization_id),
                engine=engine,
                isolation_key=isolation_key,
                worker_id=_worker_id(),
            )

        threading.Thread(
            target=self._run_session,
            args=(session_id, engine, initial_url.strip(), isolation_key, storage_state),
            daemon=True,
            name=f"browser-pw-{session_id}",
        ).start()

    def _process_actions(self, key: str, local_page: object) -> None:
        import queue

        while True:
            with _lock:
                live = _sessions.get(key)
                if not live or live.stop_requested or live.state == BrowserSessionState.STOPPED:
                    break
            try:
                action = live._action_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            except AttributeError:
                continue

            try:
                if action.get("screenshot"):
                    data = local_page.screenshot(type="png", timeout=30_000)
                    action["result_holder"].append(data)
                else:
                    res = run_playwright_action(
                        local_page,
                        action_type=action["action_type"],
                        params=action["params"],
                        timeout_ms=action["timeout_ms"],
                        source_domain=action["source_domain"],
                    )
                    action["result_holder"].append(res)
            except Exception as e:
                action["result_holder"].append(
                    {
                        "lifecycle": "failed",
                        "summary": "Internal error in session worker thread.",
                        "detail": str(e),
                    }
                )
            finally:
                action["result_event"].set()

    def _run_session(
        self,
        session_id: UUID,
        engine: BrowserEngine,
        initial_url: str,
        isolation_key: str,
        storage_state: dict | None,
    ) -> None:
        key = _key(session_id)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self._fail(
                key,
                "playwright package not installed; pip install playwright && playwright install chromium",
            )
            return

        with _lock:
            live = _sessions.get(key)
            if not live or live.stop_requested:
                return
            live.state = BrowserSessionState.STARTING
            live.latest_action_summary = "Starting browser engine"

        pw = None
        browser = None
        context = None
        page = None
        try:
            pw = sync_playwright().start()
            launch_kw = _chromium_launch_kwargs(self._settings, engine)
            browser = pw.chromium.launch(**launch_kw)
            _profile_dir(self._settings, isolation_key)
            ctx_kw: dict = {
                "viewport": {"width": 1280, "height": 720},
                "locale": "en-US",
                "user_agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                ),
                "extra_http_headers": {
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            }
            if storage_state:
                ctx_kw["storage_state"] = storage_state
            context = browser.new_context(**ctx_kw)
            page = context.new_page()
            timeout = self._settings.browser_navigation_timeout_ms
            page.set_default_navigation_timeout(timeout)

            with _lock:
                live = _sessions.get(key)
                if not live or live.stop_requested:
                    raise RuntimeError("stop requested before navigation")

            response = page.goto(initial_url, wait_until="domcontentloaded", timeout=timeout)
            final_url = page.url
            title = page.title() or ""
            status = response.status if response else 0
            nav = classify_http_status(status, url=initial_url)
            if nav.outcome == NavigationOutcome.NEEDS_USER_ACTION:
                local_page = page
                with _lock:
                    live = _sessions.get(key)
                    if live:
                        live._playwright = pw
                        live._browser = browser
                        live._context = context
                        live._page = page
                        pw = browser = context = page = None
                self._needs_user_action(
                    key,
                    attempted_url=final_url or initial_url,
                    summary=nav.user_message,
                    error_summary=nav.error_summary,
                    keep_browser=True,
                )
                self._process_actions(key, local_page)
                return
            if nav.outcome == NavigationOutcome.FAILED:
                raise RuntimeError(nav.error_summary or nav.user_message)

            local_page = page
            with _lock:
                live = _sessions.get(key)
                if not live:
                    return
                live._playwright = pw
                live._browser = browser
                live._context = context
                live._page = page
                pw = browser = context = page = None  # ownership in live
                live.state = BrowserSessionState.RUNNING
                live.started_at = datetime.now(UTC)
                live.current_url = final_url
                live.latest_action_summary = (
                    f"Loaded {final_url[:120]} (HTTP {status}, title: {title[:80] or '—'})"
                )
                logger.info(
                    "browser.session_started session=%s engine=%s url=%s status=%s",
                    session_id,
                    engine.value,
                    final_url,
                    status,
                )
            self._process_actions(key, local_page)
        except Exception as exc:
            logger.exception("browser.session_failed session=%s", session_id)
            self._cleanup_handles(pw, browser, context)
            nav = classify_navigation_exception(exc, url=initial_url)
            if nav.outcome == NavigationOutcome.NEEDS_USER_ACTION:
                local_page = page
                with _lock:
                    live = _sessions.get(key)
                    if live and page is not None:
                        live._playwright = pw
                        live._browser = browser
                        live._context = context
                        live._page = page
                        pw = browser = context = page = None
                self._needs_user_action(
                    key,
                    attempted_url=initial_url,
                    summary=nav.user_message,
                    error_summary=nav.error_summary,
                    keep_browser=page is not None,
                )
                if page is not None:
                    self._process_actions(key, local_page)
            else:
                self._fail(key, nav.error_summary or str(exc)[:500], summary=nav.user_message)
        finally:
            if pw or browser or context:
                self._cleanup_handles(pw, browser, context)

    def _needs_user_action(
        self,
        key: str,
        *,
        attempted_url: str,
        summary: str,
        error_summary: str | None,
        keep_browser: bool = False,
    ) -> None:
        with _lock:
            live = _sessions.get(key)
            if not live:
                return
            live.state = BrowserSessionState.NEEDS_USER_ACTION
            if not keep_browser:
                live.ended_at = datetime.now(UTC)
            elif not live.started_at:
                live.started_at = datetime.now(UTC)
            live.current_url = attempted_url
            live.error_summary = error_summary
            live.latest_action_summary = summary
        logger.info(
            "browser.session_needs_user_action session=%s url=%s keep_browser=%s",
            key,
            attempted_url[:120],
            keep_browser,
        )

    def _fail(self, key: str, message: str, *, summary: str | None = None) -> None:
        with _lock:
            live = _sessions.get(key)
            if not live:
                return
            live.state = BrowserSessionState.FAILED
            live.ended_at = datetime.now(UTC)
            live.error_summary = message
            live.latest_action_summary = summary or "Session failed"

    @staticmethod
    def _cleanup_handles(pw, browser, context) -> None:
        try:
            if context:
                context.close()
        except Exception:
            pass
        try:
            if browser:
                browser.close()
        except Exception:
            pass
        try:
            if pw:
                pw.stop()
        except Exception:
            pass

    def read_runtime(self, session_id: UUID) -> dict | None:
        key = _key(session_id)
        with _lock:
            live = _sessions.get(key)
            if not live:
                return None
            if live.state == BrowserSessionState.RUNNING and live._page is not None:
                try:
                    live.current_url = live._page.url  # type: ignore[attr-defined]
                except Exception:
                    pass
            return _as_dict(live)

    def request_stop(self, session_id: UUID) -> dict | None:
        key = _key(session_id)
        with _lock:
            live = _sessions.get(key)
            if not live:
                return None
            live.stop_requested = True
            if live.state in (
                BrowserSessionState.QUEUED,
                BrowserSessionState.STARTING,
                BrowserSessionState.RUNNING,
                BrowserSessionState.NEEDS_USER_ACTION,
            ):
                live.state = BrowserSessionState.STOPPING
                live.latest_action_summary = "Closing browser context"
            elif live.state in (
                BrowserSessionState.STOPPED,
                BrowserSessionState.FAILED,
                BrowserSessionState.COMPLETED,
            ):
                return _as_dict(live)

        self._close_live_handles(key)
        with _lock:
            live = _sessions.get(key)
            if not live:
                return None
            if live.state == BrowserSessionState.STOPPING:
                live.state = BrowserSessionState.STOPPED
                live.ended_at = datetime.now(UTC)
                live.latest_action_summary = "Browser context closed"
                logger.info("browser.session_closed session=%s outcome=stopped", session_id)
            return _as_dict(live)

    def _close_live_handles(self, key: str) -> None:
        with _lock:
            live = _sessions.get(key)
            if not live:
                return
            pw, browser, context = live._playwright, live._browser, live._context
            live._playwright = live._browser = live._context = live._page = None
        self._cleanup_handles(pw, browser, context)

    def execute_read_only_action(
        self,
        session_id: UUID,
        *,
        action_type: BrowserActionType,
        parameters: dict,
        timeout_ms: int,
        source_domain: str,
    ) -> dict | None:
        key = _key(session_id)
        with _lock:
            live = _sessions.get(key)
            if not live:
                return None
            if live._page is None:
                return {
                    "lifecycle": "failed",
                    "summary": "Browser page is not available for this session.",
                    "detail": (
                        "The supervised browser was closed (often after HTTP 403/401). "
                        "Stop this session and open a new one from the event, or use the external link."
                    ),
                    "policy_reason": "browser_page_unavailable",
                }
            if live.state not in (
                BrowserSessionState.RUNNING,
                BrowserSessionState.NEEDS_USER_ACTION,
            ):
                return {
                    "lifecycle": "blocked",
                    "summary": "Session is not in a runnable state for actions.",
                    "policy_reason": "session_not_actionable",
                }

            result_event = threading.Event()
            result_holder = []
            live._action_queue.put(
                {
                    "action_type": action_type,
                    "params": parameters,
                    "timeout_ms": timeout_ms,
                    "source_domain": source_domain,
                    "result_event": result_event,
                    "result_holder": result_holder,
                }
            )

        completed = result_event.wait(timeout=(timeout_ms / 1000.0) + 5.0)
        if not completed:
            return {
                "lifecycle": "timeout",
                "summary": "Action timed out waiting for worker thread execution.",
                "detail": f"Action timed out after {timeout_ms}ms.",
            }

        if not result_holder:
            return {
                "lifecycle": "failed",
                "summary": "Action execution failed without returning a result.",
            }

        result = result_holder[0]
        with _lock:
            live = _sessions.get(key)
            if live:
                live.latest_action_summary = result.get("summary", "Action finished")
                if result.get("current_url"):
                    live.current_url = result["current_url"]
                if result.get("lifecycle") == "needs_user_action":
                    live.state = BrowserSessionState.NEEDS_USER_ACTION
        return result

    def execute_confirmation_gated_action(
        self,
        session_id: UUID,
        *,
        action_type: BrowserActionType,
        parameters: dict,
        timeout_ms: int,
        source_domain: str,
    ) -> dict | None:
        if action_type != BrowserActionType.SUBMIT_FORM:
            return {
                "lifecycle": "blocked",
                "summary": "Unsupported confirmation-gated action.",
                "policy_reason": "unsupported_confirmation_action",
            }
        key = _key(session_id)
        with _lock:
            live = _sessions.get(key)
            if not live:
                return None
            if live.state not in (
                BrowserSessionState.RUNNING,
                BrowserSessionState.NEEDS_USER_ACTION,
            ):
                return {
                    "lifecycle": "blocked",
                    "summary": "Session is not in a runnable state for actions.",
                    "policy_reason": "session_not_actionable",
                }
        form_id = str(parameters.get("form_id") or "primary")
        label = str(parameters.get("target_label") or form_id)
        summary = f"Dry-run submit completed for «{label}»."
        with _lock:
            live = _sessions.get(key)
            if live:
                live.latest_action_summary = summary
        return {
            "lifecycle": "completed",
            "summary": summary,
            "detail": "No external form submit was performed in this MVP slice.",
            "current_url": live.current_url if live else None,
        }

    def capture_screenshot(self, session_id: UUID) -> bytes | None:
        key = _key(session_id)
        with _lock:
            live = _sessions.get(key)
            if not live or live._page is None:
                return None
            if live.state not in (
                BrowserSessionState.RUNNING,
                BrowserSessionState.NEEDS_USER_ACTION,
            ):
                return None
            result_event = threading.Event()
            result_holder: list = []
            live._action_queue.put(
                {"screenshot": True, "result_event": result_event, "result_holder": result_holder}
            )
        if not result_event.wait(timeout=45.0):
            return None
        if not result_holder:
            return None
        payload = result_holder[0]
        return payload if isinstance(payload, (bytes, bytearray)) else None

    def reset_for_tests(self) -> None:
        with _lock:
            keys = list(_sessions.keys())
        for key in keys:
            self._close_live_handles(key)
        with _lock:
            _sessions.clear()


def _as_dict(live: _LiveSession) -> dict:
    return {
        "state": live.state,
        "current_url": live.current_url,
        "latest_action_summary": live.latest_action_summary,
        "started_at": live.started_at,
        "ended_at": live.ended_at,
        "worker_id": live.worker_id,
        "stop_requested": live.stop_requested,
        "error_summary": live.error_summary,
    }
