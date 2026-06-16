"""Runtime registry — wires the live-cutover services into a single
process-wide state holder.

The `RuntimeRegistry` lives on `app.state.runtime_registry` and is
built during FastAPI startup. The runtime mode is sourced from
`LIVELEAD_ENVIRONMENT_MODE` but may be promoted/demoted at runtime
via the cutover service. Pause/rollback automatically reset the
mode here so the readiness view stays consistent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from livelead.domain.runtime.enums import EnvironmentMode
from livelead.runtime.settings import AppSettings

logger = logging.getLogger("livelead.runtime")


class RuntimeRegistry:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._mode: EnvironmentMode = self._initial_mode(settings)
        self._listeners: list[Callable[[EnvironmentMode], None]] = []

    @staticmethod
    def _initial_mode(settings: AppSettings) -> EnvironmentMode:
        raw = (settings.environment_mode or "test_like").strip().lower()
        try:
            return EnvironmentMode(raw)
        except ValueError:
            logger.warning(
                "unknown environment_mode=%r; defaulting to test_like", raw
            )
            return EnvironmentMode.TEST_LIKE

    @property
    def mode(self) -> EnvironmentMode:
        return self._mode

    def set_mode(self, new_mode: EnvironmentMode) -> None:
        if new_mode == self._mode:
            return
        logger.info("runtime_mode_change from=%s to=%s", self._mode.value, new_mode.value)
        self._mode = new_mode
        for listener in list(self._listeners):
            try:
                listener(new_mode)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("runtime_mode_listener_failed: %s", exc)

    def add_mode_listener(self, listener: Callable[[EnvironmentMode], None]) -> None:
        self._listeners.append(listener)

    @property
    def settings(self) -> AppSettings:
        return self._settings
