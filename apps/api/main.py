"""LiveLead web-api — composition root only."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from livelead.application.auth import AuthService
from livelead.domain.identity import LoginRateLimiter
from livelead.infrastructure.db.models import Base
from livelead.infrastructure.db.session import (
    create_engine,
    create_session_factory,
    ensure_sqlite_parent,
)
from livelead.infrastructure.observability.hooks import register_observability_hooks
from livelead.infrastructure.queue.broker import ping_redis
from livelead.interfaces.auth.tenant_context import configure_auth_boundary
from livelead.interfaces.rest.admin_connectors import router as admin_connectors_router
from livelead.interfaces.rest.audit_log import router as audit_log_router
from livelead.interfaces.rest.auth import router as auth_router
from livelead.interfaces.rest.member_management import (
    invite_router as member_invitations_router,
    router as member_management_router,
)
from livelead.interfaces.rest.browser_profiles import router as browser_profiles_router
from livelead.interfaces.rest.cloakbrowser_policy import router as cloakbrowser_policy_router
from livelead.interfaces.rest.browser_sessions import router as browser_sessions_router
from livelead.interfaces.rest.campaign_sources import router as campaign_sources_router
from livelead.interfaces.rest.campaigns import router as campaigns_router
from livelead.interfaces.rest.content import router as content_router
from livelead.interfaces.rest.dashboard import router as dashboard_router
from livelead.interfaces.rest.discovery_jobs import router as discovery_jobs_router
from livelead.interfaces.rest.events import router as events_router
from livelead.interfaces.rest.health import router as health_router
from livelead.interfaces.rest.leads import router as leads_router
from livelead.interfaces.rest.middleware import RequestLoggingMiddleware
from livelead.interfaces.rest.reminders import router as reminders_router
from livelead.interfaces.rest.report_export import router as report_export_router
from livelead.interfaces.rest.reports import router as reports_router
from livelead.runtime.settings import parse_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = parse_settings()
    ensure_sqlite_parent(settings)
    engine = create_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    try:
        subprocess.run(["bash", "scripts/ensure-db-schema.sh"], check=True, cwd=root, timeout=60)
    except Exception as exc:
        logging.getLogger("livelead.api").warning("ensure-db-schema skipped: %s", exc)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        app.state.sqlite_ok = True
    except Exception:
        app.state.sqlite_ok = False
    app.state.redis_ok = ping_redis(settings)
    # US-027 — auth boundary wiring
    configure_auth_boundary(allow_dev_headers=settings.auth_allow_dev_headers)
    app.state.auth_rate_limiter = LoginRateLimiter(
        threshold=settings.auth_rate_limit_threshold,
        window_seconds=float(settings.auth_rate_limit_window_seconds),
        lockout_seconds=float(settings.auth_rate_limit_lockout_seconds),
    )
    app.state.auth_service_factory = None  # populated by get_tenant_context via dependency

    from livelead.interfaces.auth.session_resolver import _RequestSessionProxy

    app.state.auth_service_factory = _RequestSessionProxy(app)

    # US-027 — bootstrap a default owner on a fresh install so a developer
    # can sign in without a separate CLI step. The bootstrap is a no-op once
    # at least one user exists in the workspace.
    try:
        from uuid import UUID

        from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

        org_id = UUID(settings.auth_default_organization_id) if settings.auth_default_organization_id else DEV_ORGANIZATION_ID
        async with app.state.session_factory() as sess:
            await AuthService(sess).ensure_default_owner(
                email=settings.auth_default_owner_email,
                password=settings.auth_default_owner_password,
                display_name=settings.auth_default_owner_name,
                organization_id=org_id,
            )
    except Exception as exc:
        logging.getLogger("livelead.api").warning("default owner bootstrap skipped: %s", exc)

    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="LiveLead API", lifespan=lifespan)
    register_observability_hooks(app)
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(campaign_sources_router)
    app.include_router(campaigns_router)
    app.include_router(admin_connectors_router)
    app.include_router(discovery_jobs_router)
    app.include_router(events_router)
    app.include_router(content_router)
    app.include_router(leads_router)
    app.include_router(reminders_router)
    app.include_router(dashboard_router)
    app.include_router(report_export_router)
    app.include_router(reports_router)
    app.include_router(browser_sessions_router)
    app.include_router(browser_profiles_router)
    app.include_router(cloakbrowser_policy_router)
    app.include_router(audit_log_router)
    app.include_router(member_management_router)
    app.include_router(member_invitations_router)
    return app


app = create_app()
