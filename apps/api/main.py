"""LiveLead web-api — composition root only."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from livelead.infrastructure.db.models import Base
from livelead.infrastructure.db.session import (
    create_engine,
    create_session_factory,
    ensure_sqlite_parent,
)
from livelead.infrastructure.observability.hooks import register_observability_hooks
from livelead.infrastructure.queue.broker import ping_redis
from livelead.interfaces.rest.admin_connectors import router as admin_connectors_router
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
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="LiveLead API", lifespan=lifespan)
    register_observability_hooks(app)
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(health_router)
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
    return app


app = create_app()