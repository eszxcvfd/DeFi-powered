"""Process-wide session resolver used by the auth boundary (US-027)."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.auth import AuthService
from livelead.domain.identity import (
    AuthenticatedIdentity,
    SESSION_COOKIE_NAME,
)


async def resolve_identity_from_request(
    request: Request, token: str | None = None
) -> AuthenticatedIdentity | None:
    """Resolve the current request's session cookie into an identity.

    The resolver reuses the request's app state to find the live
    `AuthService` instance. Tests can override the resolver through
    `app.dependency_overrides` to inject a fake identity.
    """

    if not token:
        token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    state: Any = getattr(request.app, "state", None)
    factory = getattr(state, "auth_service_factory", None) if state else None
    if factory is None:
        return None

    auth_service = factory()
    identity = await auth_service.resolve_session(token=token)
    return identity


class _RequestSessionProxy:
    """Adapter that gives the resolver a fresh `AuthService` per request.

    The proxy holds a reference to the running FastAPI app so it can pull
    a session from the app's session factory. The underlying session is
    scoped to the dependency request and is closed by FastAPI's
    `get_db_session` cleanup.
    """

    def __init__(self, app: Any) -> None:
        self._app = app

    def __call__(self) -> AuthService:
        # We need a fresh AsyncSession for resolve_session; the resolver
        # path is read-only and never commits. The lifetime of this
        # session is the same as the request that triggered it.
        from contextlib import asynccontextmanager

        from livelead.infrastructure.db.session import create_session_factory

        factory = getattr(self._app.state, "session_factory", None)
        if factory is None:
            raise RuntimeError("session factory not initialised")
        return _BoundAuthService(factory)


class _BoundAuthService:
    """A short-lived AuthService wrapper that lazily opens a session.

    `AuthService` expects an `AsyncSession` in its constructor, but the
    resolver path does not have access to the dependency-injected
    session. The wrapper holds a session factory and opens a session
    for each operation, then closes it. This is safe because the
    resolver only ever calls `resolve_session`, which is read-only.
    """

    def __init__(self, factory) -> None:  # type: ignore[no-untyped-def]
        self._factory = factory

    async def resolve_session(self, *, token: str) -> AuthenticatedIdentity | None:
        async with self._factory() as sess:  # type: ignore[attr-defined]
            service = AuthService(sess)
            return await service.resolve_session(token=token)
