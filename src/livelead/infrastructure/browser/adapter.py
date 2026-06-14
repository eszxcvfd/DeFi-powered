"""Facade for browser session worker lifecycle (real Playwright or stub for tests)."""

from __future__ import annotations

from uuid import UUID

from livelead.domain.browser.actions import BrowserActionType
from livelead.domain.browser.models import BrowserEngine
from livelead.infrastructure.browser.factory import (
    get_browser_runtime,
    reset_runtime_cache_for_tests,
)


def schedule_session_start(
    *,
    session_id: UUID,
    organization_id: UUID,
    engine: BrowserEngine,
    initial_url: str,
    isolation_key: str,
    storage_state: dict | None = None,
) -> None:
    get_browser_runtime().schedule_session_start(
        session_id=session_id,
        organization_id=organization_id,
        engine=engine,
        initial_url=initial_url,
        isolation_key=isolation_key,
        storage_state=storage_state,
    )


def read_runtime(session_id: UUID) -> dict | None:
    return get_browser_runtime().read_runtime(session_id)


def request_stop(session_id: UUID) -> dict | None:
    return get_browser_runtime().request_stop(session_id)


def execute_read_only_action(
    session_id: UUID,
    *,
    action_type: BrowserActionType,
    parameters: dict,
    timeout_ms: int,
    source_domain: str,
) -> dict | None:
    return get_browser_runtime().execute_read_only_action(
        session_id,
        action_type=action_type,
        parameters=parameters,
        timeout_ms=timeout_ms,
        source_domain=source_domain,
    )


def execute_confirmation_gated_action(
    session_id: UUID,
    *,
    action_type: BrowserActionType,
    parameters: dict,
    timeout_ms: int,
    source_domain: str,
) -> dict | None:
    return get_browser_runtime().execute_confirmation_gated_action(
        session_id,
        action_type=action_type,
        parameters=parameters,
        timeout_ms=timeout_ms,
        source_domain=source_domain,
    )


def capture_session_screenshot(session_id: UUID) -> bytes | None:
    return get_browser_runtime().capture_screenshot(session_id)


def reset_runtime_for_tests() -> None:
    reset_runtime_cache_for_tests()
    get_browser_runtime().reset_for_tests()
