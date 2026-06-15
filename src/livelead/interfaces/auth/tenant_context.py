"""Tenant and authentication context at the HTTP boundary (US-027).

The boundary resolves a `TenantContext` from a real session cookie when
one is present. When `auth_allow_dev_headers` is true (the default in
tests and the development environment) the legacy `X-Organization-Id`
and `X-Actor-Role` headers are used as a fallback so the existing
verification scripts can still drive the routes.

The header path is intentionally narrow: it only returns a fallback
context, never a stronger one than the session, and it never overrides
a real authenticated identity. Production deployments should set
`auth_allow_dev_headers=false` so the boundary is forced through the
session path.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Cookie, Header, HTTPException, Request

from livelead.domain.identity import (
    AuthenticatedIdentity,
    Role,
    SESSION_COOKIE_NAME,
    is_known_role,
    parse_role,
)

# Seeded in migration for local/dev flows (US-002).
DEV_ORGANIZATION_ID = UUID("00000000-0000-4000-8000-000000000001")


@dataclass(frozen=True, slots=True)
class TenantContext:
    organization_id: UUID
    actor_role: str = "viewer"
    actor_id: str = ""
    session_id: UUID | None = None
    authenticated: bool = False
    email: str = ""
    display_name: str = ""

    @property
    def role(self) -> Role | None:
        return parse_role(self.actor_role)

    def is_authenticated(self) -> bool:
        return self.authenticated

    def is_admin(self) -> bool:
        role = self.role
        return role in (Role.OWNER, Role.ADMIN)


class _AuthState:
    """Process-wide holder for the current rate limiter and the allow flag.

    The settings are read at request time, so the state is just a small
    mutable carrier. Tests can override the cookie name through FastAPI's
    dependency overrides.
    """

    allow_dev_headers: bool = True


def configure_auth_boundary(*, allow_dev_headers: bool) -> None:
    _AuthState.allow_dev_headers = bool(allow_dev_headers)


def is_auth_boundary_open() -> bool:
    return _AuthState.allow_dev_headers


def _resolve_role_from_header(value: str | None) -> str:
    candidate = (value or "").strip().lower() or "viewer"
    if not is_known_role(candidate):
        return "viewer"
    return candidate


async def get_tenant_context(
    request: Request,
    livelead_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
    x_actor_role: str | None = Header(default="analyst", alias="X-Actor-Role"),
) -> TenantContext:
    """Resolve the calling tenant from session, then header fallback.

    The session path is preferred whenever the request carries a session
    cookie. The header fallback is only used when the cookie is missing
    *and* the deployment is configured to allow it.
    """

    identity: AuthenticatedIdentity | None = getattr(request.state, "identity", None)
    if identity is None and livelead_session:
        # The auth router is responsible for populating request.state.identity
        # through a small middleware or by calling resolve_session. The
        # dependency layer here is the late stage; the cookie is the signal.
        from livelead.interfaces.auth.session_resolver import resolve_identity_from_request

        identity = await resolve_identity_from_request(request, livelead_session)

    if identity is not None:
        return TenantContext(
            organization_id=identity.organization_id,
            actor_role=identity.role.value,
            actor_id=str(identity.user_id),
            session_id=identity.session_id,
            authenticated=True,
            email=identity.email,
            display_name=identity.display_name,
        )

    if _AuthState.allow_dev_headers:
        if x_organization_id:
            try:
                org_id = UUID(x_organization_id)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="invalid X-Organization-Id") from exc
        else:
            org_id = DEV_ORGANIZATION_ID
        return TenantContext(
            organization_id=org_id,
            actor_role=_resolve_role_from_header(x_actor_role),
            actor_id="",
            session_id=None,
            authenticated=False,
        )

    raise HTTPException(status_code=401, detail="authentication required")


def require_scoring_editor(ctx: TenantContext) -> None:
    if ctx.actor_role not in ("analyst", "admin", "owner"):
        raise HTTPException(status_code=403, detail="role cannot edit scoring weights")
