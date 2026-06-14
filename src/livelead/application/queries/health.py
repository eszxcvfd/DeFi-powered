"""Health/smoke query — no domain data."""

from livelead import __version__
from livelead.runtime.health import HealthStatus, RuntimeComponentStatus
from livelead.runtime.settings import AppSettings


async def get_health_status(settings: AppSettings, *, sqlite_ok: bool, redis_ok: bool) -> HealthStatus:
    components = [
        RuntimeComponentStatus(
            name="sqlite",
            status="ok" if sqlite_ok else "unavailable",
            detail=str(settings.sqlite_path),
        ),
        RuntimeComponentStatus(
            name="redis",
            status="ok" if redis_ok else "degraded",
            detail=settings.redis_url,
        ),
    ]
    overall = "ok" if sqlite_ok else "degraded"
    return HealthStatus(
        version=__version__,
        environment=settings.environment,
        status=overall,
        components=components,
    )