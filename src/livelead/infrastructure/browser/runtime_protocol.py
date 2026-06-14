"""Browser session runtime contract (worker-side lifecycle)."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from livelead.domain.browser.actions import BrowserActionType
from livelead.domain.browser.models import BrowserEngine


class BrowserSessionRuntime(Protocol):
    def schedule_session_start(
        self,
        *,
        session_id: UUID,
        organization_id: UUID,
        engine: BrowserEngine,
        initial_url: str,
        isolation_key: str,
        storage_state: dict | None = None,
    ) -> None: ...

    def read_runtime(self, session_id: UUID) -> dict | None: ...

    def request_stop(self, session_id: UUID) -> dict | None: ...

    def execute_read_only_action(
        self,
        session_id: UUID,
        *,
        action_type: BrowserActionType,
        parameters: dict,
        timeout_ms: int,
        source_domain: str,
    ) -> dict | None: ...

    def execute_confirmation_gated_action(
        self,
        session_id: UUID,
        *,
        action_type: BrowserActionType,
        parameters: dict,
        timeout_ms: int,
        source_domain: str,
    ) -> dict | None: ...

    def capture_screenshot(self, session_id: UUID) -> bytes | None: ...

    def reset_for_tests(self) -> None: ...
