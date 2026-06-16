"""Runtime readiness application service (US-040).

Aggregates environment-profile data, the launch-gate report, live
toggle state, backup freshness, and worker heartbeats into a single
`EnvironmentProfile` read for the `/health/ready` and
`/admin/runtime-readiness` endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

from livelead.domain.runtime.enums import (
    BackupFreshness,
    EnvironmentMode,
    LiveIntegration,
    LiveToggleState,
)
from livelead.domain.runtime.gate import (
    DEV_SECRET_MASTER_KEY_PLACEHOLDER,
    evaluate_launch_gate,
)
from livelead.domain.runtime.models import (
    BackupSnapshot,
    EnvironmentProfile,
    LaunchGateReport,
    LiveIntegrationToggle,
    WorkerHeartbeat,
)
from livelead.infrastructure.db.repositories.runtime import (
    BackupSnapshotRepository,
    LiveIntegrationToggleRepository,
    WorkerHeartbeatRepository,
)
from livelead.infrastructure.queue.broker import ping_redis
from livelead.runtime.settings import AppSettings


@dataclass(frozen=True, slots=True)
class RuntimeStatusInputs:
    sqlite_writable: bool
    redis_reachable: bool
    last_backup: BackupSnapshot | None
    worker_heartbeat: WorkerHeartbeat | None
    backup_count: int


class RuntimeReadinessService:
    def __init__(
        self,
        session,
        *,
        settings: AppSettings,
        environment_mode_provider: Callable[[], EnvironmentMode],
        backup_max_age_hours: float,
        heartbeat_max_age_seconds: float,
    ) -> None:
        self._session = session
        self._settings = settings
        self._mode_provider = environment_mode_provider
        self._backup_max_age_hours = float(backup_max_age_hours)
        self._heartbeat_max_age_seconds = float(heartbeat_max_age_seconds)
        self._backups = BackupSnapshotRepository(session)
        self._toggles = LiveIntegrationToggleRepository(session)
        self._heartbeats = WorkerHeartbeatRepository(session)

    async def gather_inputs(self) -> RuntimeStatusInputs:
        return RuntimeStatusInputs(
            sqlite_writable=self._probe_sqlite(),
            redis_reachable=ping_redis(self._settings),
            last_backup=await self._backups.latest(),
            worker_heartbeat=await self._heartbeats.latest(),
            backup_count=await self._backups.count_verified_or_recorded(),
        )

    async def build_profile(
        self,
        *,
        organization_id=None,
        inputs: RuntimeStatusInputs | None = None,
    ) -> EnvironmentProfile:
        runtime_inputs = inputs or await self.gather_inputs()
        mode = self._mode_provider()
        gate = evaluate_launch_gate(
            environment_mode=mode,
            auth_allow_dev_headers=self._settings.auth_allow_dev_headers,
            auth_cookie_secure=self._settings.auth_cookie_secure,
            secret_master_key=self._settings.secret_master_key,
            sqlite_writable=runtime_inputs.sqlite_writable,
            sqlite_path=str(self._settings.sqlite_path),
            redis_reachable=runtime_inputs.redis_reachable,
            heartbeat=runtime_inputs.worker_heartbeat,
            backup_max_age_hours=self._backup_max_age_hours,
            heartbeat_max_age_seconds=self._heartbeat_max_age_seconds,
            last_backup=runtime_inputs.last_backup,
        )
        toggles: list[LiveIntegrationToggle] = []
        if organization_id is not None:
            toggles = await self._toggles.list_for_org(organization_id)
        else:
            toggles = [
                LiveIntegrationToggle(
                    integration=integration, state=LiveToggleState.DISABLED
                )
                for integration in LiveIntegration
            ]
        freshness = (
            runtime_inputs.last_backup.freshness(max_age_hours=self._backup_max_age_hours)
            if runtime_inputs.last_backup
            else BackupFreshness.UNKNOWN
        )
        return EnvironmentProfile(
            mode=mode,
            gate=gate,
            toggles=tuple(toggles),
            last_backup=runtime_inputs.last_backup,
            backup_freshness=freshness,
            worker_heartbeat=runtime_inputs.worker_heartbeat,
            auth_allow_dev_headers=self._settings.auth_allow_dev_headers,
            auth_cookie_secure=self._settings.auth_cookie_secure,
            secret_master_key_is_default=(
                self._settings.secret_master_key == DEV_SECRET_MASTER_KEY_PLACEHOLDER
            ),
            tls_terminated=bool(self._settings.auth_cookie_secure),
            redis_reachable=runtime_inputs.redis_reachable,
            sqlite_writable=runtime_inputs.sqlite_writable,
        )

    def _probe_sqlite(self) -> bool:
        path = self._settings.sqlite_path
        if not path.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(exist_ok=True)
            except OSError:
                return False
        try:
            import sqlite3

            with sqlite3.connect(str(path)) as conn:
                conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False
