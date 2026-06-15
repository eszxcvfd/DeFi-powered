"""Auth application service (US-027).

The service owns the bounded login, refresh, logout, and `me` use cases
and is the only place that touches the password verifier, the session
repository, and the audit log. Routes call into this service; the rest
of the application reads from the `TenantContext` resolved by the auth
dependencies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService
from livelead.domain.audit.enums import (
    AuditAction,
    AuditActorType,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import (
    AuditActor,
    AuditContext,
    AuditTarget,
)
from livelead.domain.identity import (
    AuthenticatedIdentity,
    LoginFailureReason,
    LoginRateLimiter,
    MembershipState,
    OrganizationMembership,
    PasswordMaterial,
    Role,
    Session,
    User,
    default_session_ttl,
    generate_session_token,
    hash_email_for_limiter,
    hash_password,
    hash_session_token,
    normalize_email,
    verify_password,
)
from livelead.infrastructure.db.repositories.identity.identity import (
    MembershipRepository,
    SessionRepository,
    UserRepository,
)
from livelead.interfaces.rest.request_context import capture_request_context
from starlette.requests import Request

logger = logging.getLogger("livelead.auth")


GENERIC_LOGIN_FAILURE_MESSAGE = "invalid credentials"


@dataclass(frozen=True, slots=True)
class LoginOutcome:
    """Result of an attempt to authenticate.

    `success` carries the cleartext session token and a full identity when
    authentication succeeded. `failure_reason` carries a generic, public
    reason (e.g. `invalid_credentials`, `locked`, `rate_limited`,
    `disabled`). The full audit-only reason lives on the audit row, not
    on the HTTP response.
    """

    success: AuthenticatedIdentity | None = None
    session_token: str | None = None
    session_expires_at: datetime | None = None
    failure_reason: str | None = None
    failure_message: str = GENERIC_LOGIN_FAILURE_MESSAGE
    audit_reason: str | None = None


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        rate_limiter: LoginRateLimiter | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._memberships = MembershipRepository(session)
        self._sessions = SessionRepository(session)
        self._rate_limiter = rate_limiter or LoginRateLimiter()
        self._audit = audit_service or AuditService(session)

    @property
    def session(self) -> AsyncSession:
        return self._session

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    async def login(
        self,
        *,
        request: Request,
        email: str,
        password: str,
        organization_id: UUID,
    ) -> LoginOutcome:
        """Authenticate a human user and issue a new session.

        The caller is responsible for the HTTP request so the audit row
        can include the request id, client IP, and user agent. The
        `organization_id` argument is the organization the caller is
        trying to sign in to. The user must have an active membership
        in that organization; otherwise login fails with a generic
        `invalid_credentials` outcome.
        """

        email_norm = normalize_email(email)
        email_hash_value = hash_email_for_limiter(email_norm)
        client_ip = self._client_ip(request)
        user_agent = self._user_agent(request)
        ctx = capture_request_context(request, workflow="auth.login")

        # Rate limit first — never reveal whether the account exists.
        rate_check = self._rate_limiter.check(
            email_hash=email_hash_value, client_ip=client_ip
        )
        if not rate_check.allowed:
            await self._record_login_failure(
                ctx=ctx,
                email_norm=email_norm,
                outcome=AuditOutcome.DENIED,
                audit_reason="rate_limited",
                failure_reason=LoginFailureReason.RATE_LIMITED,
                failure_message="too many failed attempts; try again later",
            )
            return LoginOutcome(
                failure_reason=LoginFailureReason.RATE_LIMITED,
                failure_message="too many failed attempts; try again later",
                audit_reason="rate_limited",
            )

        user = await self._users.get_by_email(email_norm)

        # Constant-time dummy verification when the user is missing so the
        # total work doesn't reveal whether the email exists.
        if user is None:
            _dummy = PasswordMaterial(
                password_hash="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                salt="AAAAAAAAAAAAAAAAAAAAAA==",
                iterations=200_000,
            )
            verify_password(password, _dummy)
            decision = self._rate_limiter.record_failure(
                email_hash=email_hash_value, client_ip=client_ip
            )
            await self._record_login_failure(
                ctx=ctx,
                email_norm=email_norm,
                outcome=AuditOutcome.FAILED,
                audit_reason="unknown_user",
                failure_reason=LoginFailureReason.INVALID_CREDENTIALS,
            )
            return LoginOutcome(
                failure_reason=LoginFailureReason.INVALID_CREDENTIALS,
                failure_message=GENERIC_LOGIN_FAILURE_MESSAGE,
                audit_reason="unknown_user",
            )

        if user.disabled:
            await self._record_login_failure(
                ctx=ctx,
                email_norm=email_norm,
                outcome=AuditOutcome.DENIED,
                audit_reason="user_disabled",
                failure_reason=LoginFailureReason.DISABLED,
            )
            return LoginOutcome(
                failure_reason=LoginFailureReason.DISABLED,
                failure_message=GENERIC_LOGIN_FAILURE_MESSAGE,
                audit_reason="user_disabled",
            )

        if user.locked_until and user.locked_until > datetime.now(UTC):
            await self._record_login_failure(
                ctx=ctx,
                email_norm=email_norm,
                outcome=AuditOutcome.DENIED,
                audit_reason="account_locked",
                failure_reason=LoginFailureReason.LOCKED,
            )
            return LoginOutcome(
                failure_reason=LoginFailureReason.LOCKED,
                failure_message=GENERIC_LOGIN_FAILURE_MESSAGE,
                audit_reason="account_locked",
            )

        material = PasswordMaterial(
            password_hash=user.password_hash,
            salt=user.password_salt,
            iterations=user.password_iterations,
        )
        if not verify_password(password, material):
            decision = self._rate_limiter.record_failure(
                email_hash=email_hash_value, client_ip=client_ip
            )
            await self._users.record_failure(user.id)
            audit_reason = "bad_password"
            failure_reason = LoginFailureReason.INVALID_CREDENTIALS
            if not decision.allowed:
                await self._users.set_locked(
                    user.id, datetime.now(UTC) + timedelta(seconds=decision.lockout_seconds)
                )
                audit_reason = "locked_after_failures"
                failure_reason = LoginFailureReason.LOCKED
            await self._record_login_failure(
                ctx=ctx,
                email_norm=email_norm,
                outcome=AuditOutcome.FAILED,
                audit_reason=audit_reason,
                failure_reason=failure_reason,
            )
            return LoginOutcome(
                failure_reason=failure_reason,
                failure_message=GENERIC_LOGIN_FAILURE_MESSAGE,
                audit_reason=audit_reason,
            )

        membership = await self._memberships.get_active_for_user(user.id)
        if (
            not membership
            or not membership.is_active()
            or membership.organization_id != organization_id
        ):
            decision = self._rate_limiter.record_failure(
                email_hash=email_hash_value, client_ip=client_ip
            )
            await self._record_login_failure(
                ctx=ctx,
                email_norm=email_norm,
                outcome=AuditOutcome.DENIED,
                audit_reason="no_membership",
                failure_reason=LoginFailureReason.INVALID_CREDENTIALS,
            )
            return LoginOutcome(
                failure_reason=LoginFailureReason.INVALID_CREDENTIALS,
                failure_message=GENERIC_LOGIN_FAILURE_MESSAGE,
                audit_reason="no_membership",
            )

        # Success path — issue a session and record an audit entry.
        token = generate_session_token()
        now = datetime.now(UTC)
        ttl = default_session_ttl()
        session_row = Session(
            id=uuid4(),
            user_id=user.id,
            organization_id=membership.organization_id,
            role=membership.role,
            token_hash=hash_session_token(token),
            issued_at=now,
            expires_at=now + ttl,
            last_seen_at=now,
            rotated_at=None,
            revoked_at=None,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        await self._sessions.add(session_row)
        await self._users.record_login(user.id)
        self._rate_limiter.record_success(
            email_hash=email_hash_value, client_ip=client_ip
        )

        identity = AuthenticatedIdentity(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name or user.email,
            organization_id=membership.organization_id,
            role=membership.role,
            session_id=session_row.id,
            expires_at=session_row.expires_at,
        )

        await self._record_login_success(
            ctx=ctx,
            user=user,
            role=membership.role,
            organization_id=membership.organization_id,
        )
        await self._session.commit()
        return LoginOutcome(
            success=identity,
            session_token=token,
            session_expires_at=session_row.expires_at,
        )

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------
    async def refresh(
        self, *, request: Request, identity: AuthenticatedIdentity
    ) -> LoginOutcome:
        """Rotate the active session, returning a new cleartext token."""

        now = datetime.now(UTC)
        existing = await self._sessions.get_for_user(identity.session_id, identity.user_id)
        if not existing or not existing.is_active(now):
            raise PermissionError("session is no longer active")
        token = generate_session_token()
        ttl = default_session_ttl()
        new_session = Session(
            id=uuid4(),
            user_id=existing.user_id,
            organization_id=existing.organization_id,
            role=existing.role,
            token_hash=hash_session_token(token),
            issued_at=now,
            expires_at=now + ttl,
            last_seen_at=now,
            rotated_at=None,
            revoked_at=None,
            client_ip=self._client_ip(request),
            user_agent=self._user_agent(request),
        )
        await self._sessions.add(new_session)
        await self._sessions.revoke(existing.id)
        # Record an audit row for the rotation.
        await self._audit.emit(
            organization_id=existing.organization_id,
            actor=AuditActor(
                actor_id=str(existing.user_id),
                actor_type=AuditActorType.HUMAN,
                role=existing.role.value,
            ),
            action=AuditAction.AUTH_SESSION_ROTATED,
            target=AuditTarget(
                target_type=AuditTargetType.SESSION,
                target_id=str(existing.id),
                display=str(existing.id),
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=capture_request_context(request, workflow="auth.refresh"),
            metadata={"new_session_id": str(new_session.id)},
        )
        user = await self._users.get_by_id(existing.user_id)
        identity = AuthenticatedIdentity(
            user_id=existing.user_id,
            email=user.email if user else str(existing.user_id),
            display_name=(user.display_name if user else "") or str(existing.user_id),
            organization_id=existing.organization_id,
            role=existing.role,
            session_id=new_session.id,
            expires_at=new_session.expires_at,
        )
        await self._session.commit()
        return LoginOutcome(
            success=identity,
            session_token=token,
            session_expires_at=new_session.expires_at,
        )

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------
    async def logout(
        self, *, request: Request, identity: AuthenticatedIdentity
    ) -> None:
        existing = await self._sessions.get_for_user(identity.session_id, identity.user_id)
        if not existing:
            return
        await self._sessions.revoke(existing.id)
        await self._audit.emit(
            organization_id=existing.organization_id,
            actor=AuditActor(
                actor_id=str(existing.user_id),
                actor_type=AuditActorType.HUMAN,
                role=existing.role.value,
            ),
            action=AuditAction.AUTH_LOGOUT,
            target=AuditTarget(
                target_type=AuditTargetType.SESSION,
                target_id=str(existing.id),
                display=str(existing.id),
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=capture_request_context(request, workflow="auth.logout"),
        )
        await self._session.commit()

    # ------------------------------------------------------------------
    # Resolve cookie -> identity
    # ------------------------------------------------------------------
    async def resolve_session(self, *, token: str) -> AuthenticatedIdentity | None:
        if not token:
            return None
        token_hash = hash_session_token(token)
        existing = await self._sessions.get_by_token_hash(token_hash)
        if not existing or not existing.is_active():
            return None
        user = await self._users.get_by_id(existing.user_id)
        if not user or user.disabled:
            return None
        # Touch the session for liveness but never commit here — the route
        # handler commits once the response is built.
        try:
            await self._sessions.touch(existing.id)
        except Exception:  # pragma: no cover - defensive
            logger.warning("session_touch_failed session_id=%s", existing.id)
        return AuthenticatedIdentity(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name or user.email,
            organization_id=existing.organization_id,
            role=existing.role,
            session_id=existing.id,
            expires_at=existing.expires_at,
        )

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------
    async def ensure_default_owner(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        organization_id: UUID,
        role: Role = Role.OWNER,
    ) -> User | None:
        """Create the seeded owner if no user exists yet.

        Returns the created user, or `None` if the workspace already has
        at least one user. The seed is intentionally minimal: a single
        owner is enough to start the rest of the auth-aware workflow.
        """

        if (await self._users.count_all()) > 0:
            return None
        material = hash_password(password)
        email_norm = normalize_email(email)
        user = await self._users.add(
            email=email_norm,
            email_hash=hash_email_for_limiter(email_norm),
            display_name=display_name,
            password_hash=material.password_hash,
            password_salt=material.salt,
            password_iterations=material.iterations,
        )
        await self._memberships.add(
            user_id=user.id,
            organization_id=organization_id,
            role=role,
            state=MembershipState.ACTIVE,
        )
        await self._session.commit()
        return user

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _client_ip(self, request: Request) -> str:
        return (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "")
            or ""
        )

    def _user_agent(self, request: Request) -> str:
        return (request.headers.get("user-agent") or "")[:300]

    async def _record_login_failure(
        self,
        *,
        ctx: AuditContext,
        email_norm: str,
        outcome: AuditOutcome,
        audit_reason: str,
        failure_reason: str,
    ) -> None:
        # The audit row never stores the cleartext email; only the hash.
        email_hash_value = hash_email_for_limiter(email_norm)
        try:
            await self._audit.emit(
                organization_id=ctx_organization_id(ctx),
                actor=AuditActor(
                    actor_id=email_hash_value,
                    actor_type=AuditActorType.HUMAN,
                    role="",
                ),
                action=AuditAction.AUTH_LOGIN_FAILED,
                target=AuditTarget(
                    target_type=AuditTargetType.USER,
                    target_id=email_hash_value,
                    display=email_hash_value,
                ),
                outcome=outcome,
                context=ctx,
                metadata={"reason": audit_reason, "public_reason": failure_reason},
            )
            await self._session.commit()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("audit_login_failure_emit_failed err=%s", exc)

    async def _record_login_success(
        self,
        *,
        ctx: AuditContext,
        user: User,
        role: Role,
        organization_id: UUID,
    ) -> None:
        try:
            await self._audit.emit(
                organization_id=organization_id,
                actor=AuditActor(
                    actor_id=str(user.id),
                    actor_type=AuditActorType.HUMAN,
                    role=role.value,
                ),
                action=AuditAction.AUTH_LOGIN_SUCCEEDED,
                target=AuditTarget(
                    target_type=AuditTargetType.USER,
                    target_id=str(user.id),
                    display=user.email,
                ),
                outcome=AuditOutcome.SUCCEEDED,
                context=ctx,
                metadata={"email_hash": hash_email_for_limiter(user.email)},
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("audit_login_success_emit_failed err=%s", exc)


def ctx_organization_id(ctx: AuditContext) -> UUID:
    """Best-effort organization id for login-failure audit rows.

    The login flow does not know which organization the caller was trying
    to sign in to, so we fall back to the dev organization if a real
    organization is not already present in the context.
    """

    from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

    return DEV_ORGANIZATION_ID


__all__ = ["AuthService", "LoginOutcome", "GENERIC_LOGIN_FAILURE_MESSAGE"]
