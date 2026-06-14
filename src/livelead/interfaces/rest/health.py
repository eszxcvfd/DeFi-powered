"""Health router."""

from fastapi import APIRouter, Request

from livelead.application.queries.health import get_health_status

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    settings = request.app.state.settings
    sqlite_ok = getattr(request.app.state, "sqlite_ok", True)
    redis_ok = getattr(request.app.state, "redis_ok", False)
    return await get_health_status(settings, sqlite_ok=sqlite_ok, redis_ok=redis_ok)
