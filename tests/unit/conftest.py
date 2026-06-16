"""Shared fixtures for unit tests (US-040 and follow-on)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.infrastructure.db.models import Base
from livelead.infrastructure.db.session import (
    create_engine,
    create_session_factory,
    ensure_sqlite_parent,
)
from livelead.runtime.settings import parse_settings


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    """Yield an async session against an in-memory-style SQLite file.

    Each test gets its own tempdir and database file. The schema is
    built from the current `Base.metadata`, so new tables added for
    US-040 (and later stories) are picked up automatically.
    """
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "unit.sqlite3"
        settings = parse_settings()
        settings.sqlite_path = db_path
        ensure_sqlite_parent(settings)
        engine = create_engine(settings)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = create_session_factory(engine)
        async with factory() as sess:
            yield sess
        await engine.dispose()
