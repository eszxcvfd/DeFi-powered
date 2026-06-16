"""Local pytest fixtures for the observability tests (US-041).

The shared `tests/conftest.py` creates a fresh SQLite per test and
runs the lifespan's `Base.metadata.create_all`, which builds the
schema but does not insert the seed alert rules that the
`20260616_0031_alerting` migration adds. The shared
`scripts/ensure-db-schema.sh` then trips over a duplicate column
because the schema is already there.

This conftest runs `alembic upgrade head` against the tmp_path
database directly so the seed rules are inserted before the
lifespan starts. It does not change the shared `client` fixture.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import pytest_asyncio

from apps.api.main import create_app
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from livelead.infrastructure.db.session import (
    create_engine,
    create_session_factory,
)
from livelead.runtime.settings import parse_settings

ROOT = Path(__file__).resolve().parents[2]


def _run_alembic_upgrade(db_path: str) -> None:
    env = os.environ.copy()
    env["LIVELEAD_SQLITE_PATH"] = db_path
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic upgrade failed: rc={result.returncode}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )


@pytest.fixture
def migrated_db(tmp_path, monkeypatch):
    """Run alembic upgrade head against a tmp_path SQLite and return its path."""

    db = tmp_path / "test.sqlite3"
    monkeypatch.setenv("LIVELEAD_SQLITE_PATH", str(db))
    monkeypatch.setenv("LIVELEAD_REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("LIVELEAD_AUTH_ALLOW_DEV_HEADERS", "true")
    _run_alembic_upgrade(str(db))
    # Defensive: the alembic chain in this repo does not always create
    # every table that `Base.metadata.create_all` would. The lifespan
    # runs the metadata sync in production, so we mirror it here.
    from livelead.infrastructure.db.models import Base
    from livelead.infrastructure.db.session import create_engine
    from livelead.runtime.settings import parse_settings

    settings = parse_settings()
    engine = create_engine(settings)
    import asyncio

    async def _create_all():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_all())
    import os as _os

    if engine.sync_engine is not None:  # type: ignore[attr-defined]
        engine.sync_engine.dispose()
    else:
        try:
            engine.dispose()
        except Exception:
            pass
    return str(db)


@pytest_asyncio.fixture
async def migrated_session(migrated_db):
    settings = parse_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def migrated_client(migrated_db):
    app = create_app()
    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.app = app  # type: ignore[attr-defined]
            yield ac
