import pytest
from sqlalchemy import text

from livelead.infrastructure.db.session import create_engine, ensure_sqlite_parent
from livelead.runtime.settings import AppSettings


@pytest.mark.asyncio
async def test_sqlite_bootstrap_without_domain_schema(tmp_path):
    db = tmp_path / "livelead.sqlite3"
    settings = AppSettings(sqlite_path=db)
    ensure_sqlite_parent(settings)
    engine = create_engine(settings)
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    await engine.dispose()
    assert db.exists()