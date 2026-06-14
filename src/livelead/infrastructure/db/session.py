"""Async SQLite engine factory."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from livelead.runtime.settings import AppSettings


def ensure_sqlite_parent(settings: AppSettings) -> None:
    path = settings.sqlite_path
    if path.parent and str(path.parent) not in ("", "."):
        Path(path.parent).mkdir(parents=True, exist_ok=True)


def create_engine(settings: AppSettings) -> AsyncEngine:
    ensure_sqlite_parent(settings)
    return create_async_engine(settings.database_url, echo=False)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)
