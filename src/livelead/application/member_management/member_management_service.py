"""Member-management application service (US-028).

Owns the bounded invite / accept / role-change / disable / enable /
revoke flows on top of the US-027 identity layer. Side effects
(database writes, audit rows, session revocation) live here; the
domain modules in `livelead.domain.identity` keep the rules
side-effect free.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
)
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
    InvitationAcceptanceResult,
    InvitationState,
    MemberInvitation,
    MemberListing,
    MemberManagementError,
    MembershipState,
    OrganizationMembership,
    PasswordMaterial,
    Role,
    Session,
    User,
    can_manage_member_governance,
    default_invitation_ttl,
    default_session_ttl,
    demote_would_lock_organization,
    disable_would_lock_organization,
    generate_invitation_token,
    generate_session_token,
    hash_email_for_limiter,
    hash_invitation_token,
    hash_password,
    hash_session_token,
    invitation_is_redeemable,
    is_usable_membership,
    normalize_email,
    parse_role,
    revoke_would_lock_organization,
)
from livelead.infrastructure.db.repositories.identity.identity import (
    MemberInvitationRepository,
    MembershipRepository,
    SessionRepository,
    UserRepository,
)
from livelead.interfaces.rest.request_context import capture_request_context

logger = logging.getLogger("livelead.member_management")


@dataclass(frozen=True, slots=True)
class MemberView:
    id: str
    user_id: str
    email: str
    display_name: str
    role: str
    state: str
    created_at: str
    updated_at: str
    disabled: bool
    last_login_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name,
            "role": self.role,
            "state": self.state,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "disabled": self.disabled,
            "last_login_at": self.last_login_at,
        }


@dataclass(frozen=True, slots=True)
class InvitationView:
    id: str
    email: str
    role: str
    state: str
    invited_by_user_id: str
    invited_by_email: str
    expires_at: str
    accepted_at: str | None
    revoked_at: str | None
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "state": self.state,
            "invited_by_user_id": self.invited_by_user_id,
            "invited_by_email": self.invited_by_email,
            "expires_at": self.expires_at,
            "accepted_at": self.accepted_at,
            "revoked_at": self.revoked_at,
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class InvitationCreationResult:
    invitation: InvitationView
    # Cleartext token, returned to the inviter exactly once and never
    # persisted. Subsequent reads only expose the token_hash.
    invite_token: str
    invite_url: str | None


@dataclass(frozen=True, slots=True)
class MemberListResult:
    members: list[MemberView]
    invitations: list[InvitationView]
    total_members: int
    total_invitations: int


@dataclass(frozen=True, slots=True)
class MemberActionResult:
    member: MemberView
    sessions_revoked: int = 0
    invite_token: str | None = None


class MemberManagementService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        audit_service: AuditService | None = None,
    ) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._memberships = MembershipRepository(session)
        self._sessions = SessionRepository(session)
        self._invitations = MemberInvitationRepository(session)
        self._audit = audit_service or AuditService(session)

    @property
    def session(self) -> AsyncSession:
        return self._session

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------
    async def list_organization_members(
        self,
        *,
        organization_id: UUID,
    ) -> MemberListResult:
        memberships = await self._memberships.list_for_organization(organization_id)
        invitations = await self._invitations.list_for_org(organization_id)

        member_views: list[MemberView] = []
        user_ids: list[str] = []
        for membership in memberships:
            user_ids.append(str(membership.user_id))
        users_by_id: dict[str, User] = {}
        for user_id in sorted(set(user_ids)):
            user = await self._users.get_by_id(UUID(user_id))
            if user:
                users_by_id[user_id] = user
        for membership in memberships:
            user = users_by_id.get(str(membership.user_id))
            member_views.append(
                _membership_to_view(membership, user)
            )

        inviter_ids = sorted({str(i.invited_by_user_id) for i in invitations if i.invited_by_user_id})
        inviter_emails: dict[str, str] = {}
        for inviter_id in inviter_ids:
            inviter = await self._users.get_by_id(UUID(inviter_id))
            if inviter:
                inviter_emails[inviter_id] = inviter.email

        invitation_views = [
            _invitation_to_view(inv, inviter_emails) for inv in invitations
        ]

        return MemberListResult(
            members=member_views,
            invitations=invitation_views,
            total_members=len(member_views),
            total_invitations=len(invitation_views),
        )

    # ------------------------------------------------------------------
    # Invite
    # ------------------------------------------------------------------
    async def invite_member(
        self,
        *,
        request: Request,
        organization_id: UUID,
        actor: AuthenticatedIdentity,
        email: str,
        role: Role,
    ) -> tuple[MemberActionResult | None, str | None, str | None]:
        """Create a pending invitation.

        Returns `(None, public_reason, audit_reason)` on a blocked
        outcome, or `(MemberActionResult, None, None)` on success.
        The cleartext `invite_token` is returned inside the
        `MemberActionResult.invite_token` field exactly once.
        """

        email_norm = normalize_email(email)
        ctx = capture_request_context(request, workflow="member.invite")
        actor_role = actor.role

        if not can_manage_member_governance(actor_role, role):
            await self._emit_governance_denied(
                ctx=ctx,
                organization_id=organization_id,
                actor=actor,
                action=AuditAction.MEMBER_INVITED,
                target_id=email_norm,
                reason="role_not_governable",
                metadata={"target_email_hash": hash_email_for_limiter(email_norm), "target_role": role.value},
            )
            return None, MemberManagementError.ROLE_NOT_GOVERNABLE, "role_not_governable"

        # Block duplicates: an active membership with this email, or a
        # pending invite that has not expired.
        existing_membership = await self._memberships.get_by_email(organization_id, email_norm)
        if existing_membership and is_usable_membership(existing_membership):
            await self._emit_governance_denied(
                ctx=ctx,
                organization_id=organization_id,
                actor=actor,
                action=AuditAction.MEMBER_INVITED,
                target_id=email_norm,
                reason="email_already_member",
                metadata={"target_email_hash": hash_email_for_limiter(email_norm)},
            )
            return None, MemberManagementError.EMAIL_ALREADY_MEMBER, "email_already_member"

        existing_invites = [
            inv
            for inv in await self._invitations.list_for_org(organization_id)
            if inv.email == email_norm and inv.is_pending()
        ]
        if existing_invites:
            await self._emit_governance_denied(
                ctx=ctx,
                organization_id=organization_id,
                actor=actor,
                action=AuditAction.MEMBER_INVITED,
                target_id=email_norm,
                reason="duplicate_pending_invite",
                metadata={"target_email_hash": hash_email_for_limiter(email_norm)},
            )
            return None, MemberManagementError.INVALID_STATE, "duplicate_pending_invite"

        token = generate_invitation_token()
        token_hash = hash_invitation_token(token)
        expires_at = datetime.now(UTC) + default_invitation_ttl()

        invitation = await self._invitations.add(
            organization_id=organization_id,
            email=email_norm,
            role=role,
            state=InvitationState.PENDING,
            token_hash=token_hash,
            invited_by_user_id=actor.user_id,
            expires_at=expires_at,
        )

        inviter = await self._users.get_by_id(actor.user_id)
        invitation_view = _invitation_to_view(
            invitation,
            {str(actor.user_id): inviter.email if inviter else ""},
        )

        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor.role.value, actor_id=str(actor.user_id)),
            action=AuditAction.MEMBER_INVITED,
            target=AuditTarget(
                target_type=AuditTargetType.INVITATION,
                target_id=str(invitation.id),
                display=email_norm,
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=ctx,
            metadata={
                "invitation_id": str(invitation.id),
                "target_email_hash": hash_email_for_limiter(email_norm),
                "target_role": role.value,
                "expires_at": expires_at.isoformat(),
            },
        )
        await self._session.commit()

        return (
            MemberActionResult(
                member=MemberView(
                    id="",
                    user_id="",
                    email=email_norm,
                    display_name=email_norm,
                    role=role.value,
                    state=InvitationState.PENDING.value,
                    created_at=invitation.created_at.isoformat(),
                    updated_at=invitation.updated_at.isoformat(),
                    disabled=False,
                    last_login_at=None,
                ),
                sessions_revoked=0,
                invite_token=token,
            ),
            None,
            None,
        )

    # ------------------------------------------------------------------
    # Accept
    # ------------------------------------------------------------------
    async def accept_invitation(
        self,
        *,
        request: Request,
        token: str,
        password: str,
        display_name: str | None = None,
    ) -> tuple[InvitationAcceptanceResult | None, str | None, str | None]:
        """Redeem an invitation token into an active membership.

        Returns `(InvitationAcceptanceResult, None, None)` on success.
        On failure returns `(None, public_reason, audit_reason)`.
        """

        ctx = capture_request_context(request, workflow="member.accept_invitation")
        token_hash = hash_invitation_token(token)
        invitation = await self._invitations.get_by_token_hash(token_hash)
        if invitation is None:
            return None, MemberManagementError.NOT_FOUND, "invitation_not_found"

        if invitation.state == InvitationState.REVOKED:
            return None, MemberManagementError.INVITE_REVOKED, "invitation_revoked"
        if invitation.state == InvitationState.ACCEPTED:
            return None, MemberManagementError.INVITE_ALREADY_ACCEPTED, "invitation_already_accepted"
        if invitation.state == InvitationState.EXPIRED:
            return None, MemberManagementError.INVITE_EXPIRED, "invitation_expired"
        if not invitation_is_redeemable(invitation):
            return None, MemberManagementError.INVITE_EXPIRED, "invitation_expired"

        email_norm = invitation.email
        existing_user = await self._users.get_by_email(email_norm)

        # Verify password shape before creating or linking the user.
        try:
            from livelead.domain.identity import validate_password_shape

            validate_password_shape(password)
        except ValueError as exc:
            await self._audit.emit(
                organization_id=invitation.organization_id,
                actor=AuditActor(
                    actor_id=hash_email_for_limiter(email_norm),
                    actor_type=AuditActorType.HUMAN,
                    role="",
                ),
                action=AuditAction.MEMBER_INVITATION_ACCEPTED,
                target=AuditTarget(
                    target_type=AuditTargetType.INVITATION,
                    target_id=str(invitation.id),
                    display=email_norm,
                ),
                outcome=AuditOutcome.DENIED,
                context=ctx,
                metadata={
                    "invitation_id": str(invitation.id),
                    "target_email_hash": hash_email_for_limiter(email_norm),
                    "reason": "invalid_password",
                },
            )
            await self._session.commit()
            return None, MemberManagementError.INVALID_PAYLOAD, "invalid_password"

        if existing_user is None:
            material = hash_password(password)
            user = await self._users.add(
                email=email_norm,
                email_hash=hash_email_for_limiter(email_norm),
                display_name=(display_name or email_norm).strip()[:200],
                password_hash=material.password_hash,
                password_salt=material.salt,
                password_iterations=material.iterations,
            )
            new_user = True
        else:
            # Link an existing user to the organization. The existing
            # password material is kept; the redeemer must already
            # own the account.
            if existing_user.disabled:
                await self._audit.emit(
                    organization_id=invitation.organization_id,
                    actor=AuditActor(
                        actor_id=str(existing_user.id),
                        actor_type=AuditActorType.HUMAN,
                        role="",
                    ),
                    action=AuditAction.MEMBER_INVITATION_ACCEPTED,
                    target=AuditTarget(
                        target_type=AuditTargetType.INVITATION,
                        target_id=str(invitation.id),
                        display=email_norm,
                    ),
                    outcome=AuditOutcome.DENIED,
                    context=ctx,
                    metadata={
                        "invitation_id": str(invitation.id),
                        "reason": "user_disabled",
                    },
                )
                await self._session.commit()
                return None, MemberManagementError.FORBIDDEN, "user_disabled"
            user = existing_user
            new_user = False

        existing_membership = await self._memberships.get_for_user_and_org(
            invitation.organization_id, user.id
        )
        if existing_membership and is_usable_membership(existing_membership):
            await self._audit.emit(
                organization_id=invitation.organization_id,
                actor=AuditActor(
                    actor_id=str(user.id),
                    actor_type=AuditActorType.HUMAN,
                    role="",
                ),
                action=AuditAction.MEMBER_INVITATION_ACCEPTED,
                target=AuditTarget(
                    target_type=AuditTargetType.INVITATION,
                    target_id=str(invitation.id),
                    display=email_norm,
                ),
                outcome=AuditOutcome.DENIED,
                context=ctx,
                metadata={
                    "invitation_id": str(invitation.id),
                    "reason": "already_member",
                },
            )
            await self._session.commit()
            return None, MemberManagementError.EMAIL_ALREADY_MEMBER, "already_member"

        if existing_membership is None:
            membership = await self._memberships.add(
                user_id=user.id,
                organization_id=invitation.organization_id,
                role=invitation.role,
                state=MembershipState.ACTIVE,
            )
        else:
            # Reactivate a previous (non-active) membership into the role
            # from the invitation. We never grant a role beyond the
            # invitation's intended role.
            await self._memberships.set_role(
                invitation.organization_id, existing_membership.id, invitation.role
            )
            await self._memberships.set_state(
                invitation.organization_id, existing_membership.id, MembershipState.ACTIVE
            )
            refreshed = await self._memberships.get_for_user_and_org(
                invitation.organization_id, user.id
            )
            membership = refreshed or existing_membership

        now = datetime.now(UTC)
        await self._invitations.set_state(
            invitation.id,
            InvitationState.ACCEPTED,
            accepted_by_user_id=user.id,
            accepted_at=now,
        )

        # Issue a session so the redeemer is signed in immediately.
        access_token = generate_session_token()
        ttl = default_session_ttl()
        session_row = Session(
            id=uuid4(),
            user_id=user.id,
            organization_id=invitation.organization_id,
            role=invitation.role,
            token_hash=hash_session_token(access_token),
            issued_at=now,
            expires_at=now + ttl,
            last_seen_at=now,
            rotated_at=None,
            revoked_at=None,
            client_ip=_client_ip(request),
            user_agent=_user_agent(request),
        )
        await self._sessions.add(session_row)

        await self._audit.emit(
            organization_id=invitation.organization_id,
            actor=make_actor_from_role(invitation.role.value, actor_id=str(user.id)),
            action=AuditAction.MEMBER_INVITATION_ACCEPTED,
            target=AuditTarget(
                target_type=AuditTargetType.INVITATION,
                target_id=str(invitation.id),
                display=email_norm,
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=ctx,
            metadata={
                "invitation_id": str(invitation.id),
                "user_id": str(user.id),
                "role": invitation.role.value,
                "new_user": new_user,
            },
        )
        await self._session.commit()

        return (
            InvitationAcceptanceResult(
                user_id=user.id,
                membership_id=membership.id,
                role=invitation.role,
                organization_id=invitation.organization_id,
                access_token=access_token,
                session_expires_at=session_row.expires_at,
                new_user=new_user,
            ),
            None,
            None,
        )

    # ------------------------------------------------------------------
    # Change role
    # ------------------------------------------------------------------
    async def change_member_role(
        self,
        *,
        request: Request,
        organization_id: UUID,
        actor: AuthenticatedIdentity,
        membership_id: UUID,
        new_role: Role,
    ) -> tuple[MemberActionResult | None, str | None, str | None]:
        ctx = capture_request_context(request, workflow="member.change_role")
        actor_role = actor.role
        target = await self._memberships.get_for_id(organization_id, membership_id)
        if target is None:
            return None, MemberManagementError.NOT_FOUND, "membership_not_found"
        if not can_manage_member_governance(actor_role, target.role):
            await self._emit_governance_denied(
                ctx=ctx,
                organization_id=organization_id,
                actor=actor,
                action=AuditAction.MEMBER_ROLE_CHANGED,
                target_id=str(membership_id),
                reason="role_not_governable",
                metadata={"current_role": target.role.value, "new_role": new_role.value},
            )
            return None, MemberManagementError.ROLE_NOT_GOVERNABLE, "role_not_governable"

        memberships = await self._memberships.list_for_organization(organization_id)
        if demote_would_lock_organization(
            memberships, target_membership=target, new_role=new_role
        ):
            await self._emit_governance_denied(
                ctx=ctx,
                organization_id=organization_id,
                actor=actor,
                action=AuditAction.MEMBER_ROLE_CHANGED,
                target_id=str(membership_id),
                reason="last_owner_protected",
                metadata={"current_role": target.role.value, "new_role": new_role.value},
            )
            return None, MemberManagementError.LAST_OWNER_PROTECTED, "last_owner_protected"

        previous_role = target.role
        await self._memberships.set_role(organization_id, membership_id, new_role)
        updated = await self._memberships.get_for_id(organization_id, membership_id)
        user = await self._users.get_by_id(target.user_id)
        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor.role.value, actor_id=str(actor.user_id)),
            action=AuditAction.MEMBER_ROLE_CHANGED,
            target=AuditTarget(
                target_type=AuditTargetType.MEMBERSHIP,
                target_id=str(membership_id),
                display=user.email if user else str(target.user_id),
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=ctx,
            metadata={
                "user_id": str(target.user_id),
                "previous_role": previous_role.value,
                "new_role": new_role.value,
            },
        )
        await self._session.commit()
        assert updated is not None
        return (
            MemberActionResult(
                member=_membership_to_view(updated, user),
                sessions_revoked=0,
            ),
            None,
            None,
        )

    # ------------------------------------------------------------------
    # Disable / Enable / Revoke
    # ------------------------------------------------------------------
    async def disable_member(
        self,
        *,
        request: Request,
        organization_id: UUID,
        actor: AuthenticatedIdentity,
        membership_id: UUID,
    ) -> tuple[MemberActionResult | None, str | None, str | None]:
        return await self._change_member_state(
            request=request,
            organization_id=organization_id,
            actor=actor,
            membership_id=membership_id,
            target_state=MembershipState.DISABLED,
            audit_action=AuditAction.MEMBER_DISABLED,
            block_predicate=disable_would_lock_organization,
            block_reason="last_owner_protected",
            block_code=MemberManagementError.LAST_OWNER_PROTECTED,
            revoke_sessions=True,
        )

    async def enable_member(
        self,
        *,
        request: Request,
        organization_id: UUID,
        actor: AuthenticatedIdentity,
        membership_id: UUID,
    ) -> tuple[MemberActionResult | None, str | None, str | None]:
        return await self._change_member_state(
            request=request,
            organization_id=organization_id,
            actor=actor,
            membership_id=membership_id,
            target_state=MembershipState.ACTIVE,
            audit_action=AuditAction.MEMBER_ENABLED,
            block_predicate=None,
            block_reason=None,
            block_code=None,
            revoke_sessions=False,
        )

    async def revoke_member_access(
        self,
        *,
        request: Request,
        organization_id: UUID,
        actor: AuthenticatedIdentity,
        membership_id: UUID,
    ) -> tuple[MemberActionResult | None, str | None, str | None]:
        return await self._change_member_state(
            request=request,
            organization_id=organization_id,
            actor=actor,
            membership_id=membership_id,
            target_state=MembershipState.REVOKED,
            audit_action=AuditAction.MEMBER_ACCESS_REVOKED,
            block_predicate=revoke_would_lock_organization,
            block_reason="last_owner_protected",
            block_code=MemberManagementError.LAST_OWNER_PROTECTED,
            revoke_sessions=True,
        )

    # ------------------------------------------------------------------
    # Revoke invitation
    # ------------------------------------------------------------------
    async def revoke_invitation(
        self,
        *,
        request: Request,
        organization_id: UUID,
        actor: AuthenticatedIdentity,
        invitation_id: UUID,
        reason: str | None = None,
    ) -> tuple[InvitationView | None, str | None, str | None]:
        ctx = capture_request_context(request, workflow="member.revoke_invitation")
        invitation = await self._invitations.get_for_org(organization_id, invitation_id)
        if invitation is None:
            return None, MemberManagementError.NOT_FOUND, "invitation_not_found"
        if invitation.state != InvitationState.PENDING:
            return None, MemberManagementError.INVALID_STATE, "invitation_not_pending"

        revoked = await self._invitations.set_state(
            invitation.id,
            InvitationState.REVOKED,
            revoked_by_user_id=actor.user_id,
            revoked_at=datetime.now(UTC),
            revoke_reason=(reason or "")[:300] or None,
        )
        inviter = (
            await self._users.get_by_id(invitation.invited_by_user_id)
            if invitation.invited_by_user_id
            else None
        )
        view = _invitation_to_view(
            revoked or invitation,
            {str(invitation.invited_by_user_id): inviter.email if inviter else ""} if invitation.invited_by_user_id else {},
        )
        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor.role.value, actor_id=str(actor.user_id)),
            action=AuditAction.MEMBER_INVITATION_REVOKED,
            target=AuditTarget(
                target_type=AuditTargetType.INVITATION,
                target_id=str(invitation.id),
                display=invitation.email,
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=ctx,
            metadata={
                "invitation_id": str(invitation.id),
                "target_email_hash": hash_email_for_limiter(invitation.email),
            },
        )
        await self._session.commit()
        return view, None, None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _change_member_state(
        self,
        *,
        request: Request,
        organization_id: UUID,
        actor: AuthenticatedIdentity,
        membership_id: UUID,
        target_state: MembershipState,
        audit_action: AuditAction,
        block_predicate,
        block_reason: str | None,
        block_code: str | None,
        revoke_sessions: bool,
    ) -> tuple[MemberActionResult | None, str | None, str | None]:
        ctx = capture_request_context(request, workflow=f"member.{audit_action.value}")
        actor_role = actor.role
        target = await self._memberships.get_for_id(organization_id, membership_id)
        if target is None:
            return None, MemberManagementError.NOT_FOUND, "membership_not_found"
        if not can_manage_member_governance(actor_role, target.role):
            await self._emit_governance_denied(
                ctx=ctx,
                organization_id=organization_id,
                actor=actor,
                action=audit_action,
                target_id=str(membership_id),
                reason="role_not_governable",
                metadata={"current_role": target.role.value, "target_state": target_state.value},
            )
            return None, MemberManagementError.ROLE_NOT_GOVERNABLE, "role_not_governable"

        memberships = await self._memberships.list_for_organization(organization_id)
        if block_predicate is not None and block_predicate(
            memberships, target_membership=target
        ):
            await self._emit_governance_denied(
                ctx=ctx,
                organization_id=organization_id,
                actor=actor,
                action=audit_action,
                target_id=str(membership_id),
                reason=block_reason or "blocked",
                metadata={"current_role": target.role.value, "target_state": target_state.value},
            )
            return None, block_code or MemberManagementError.FORBIDDEN, block_reason or "blocked"

        previous_state = target.state
        await self._memberships.set_state(organization_id, membership_id, target_state)
        updated = await self._memberships.get_for_id(organization_id, membership_id)
        user = await self._users.get_by_id(target.user_id)
        sessions_revoked = 0
        if revoke_sessions:
            sessions_revoked = await self._sessions.revoke_all_for_user_and_org(
                target.user_id, organization_id
            )

        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor.role.value, actor_id=str(actor.user_id)),
            action=audit_action,
            target=AuditTarget(
                target_type=AuditTargetType.MEMBERSHIP,
                target_id=str(membership_id),
                display=user.email if user else str(target.user_id),
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=ctx,
            metadata={
                "user_id": str(target.user_id),
                "previous_state": previous_state.value,
                "new_state": target_state.value,
                "sessions_revoked": sessions_revoked,
            },
        )
        await self._session.commit()
        assert updated is not None
        return (
            MemberActionResult(
                member=_membership_to_view(updated, user),
                sessions_revoked=sessions_revoked,
            ),
            None,
            None,
        )

    async def _emit_governance_denied(
        self,
        *,
        ctx: AuditContext,
        organization_id: UUID,
        actor: AuthenticatedIdentity,
        action: AuditAction,
        target_id: str,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"reason": reason}
        if metadata:
            payload.update(metadata)
        try:
            await self._audit.emit(
                organization_id=organization_id,
                actor=make_actor_from_role(actor.role.value, actor_id=str(actor.user_id)),
                action=AuditAction.MEMBER_GOVERNANCE_DENIED,
                target=AuditTarget(
                    target_type=AuditTargetType.SYSTEM,
                    target_id=target_id,
                    display=target_id,
                ),
                outcome=AuditOutcome.DENIED,
                context=ctx,
                metadata={
                    "denied_action": action.value,
                    **payload,
                },
            )
            await self._session.commit()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("member_governance_denied_emit_failed err=%s", exc)


def _membership_to_view(
    membership: OrganizationMembership, user: User | None
) -> MemberView:
    return MemberView(
        id=str(membership.id),
        user_id=str(membership.user_id),
        email=user.email if user else "",
        display_name=(user.display_name or user.email) if user else "",
        role=membership.role.value,
        state=membership.state.value,
        created_at=membership.created_at.isoformat(),
        updated_at=membership.updated_at.isoformat(),
        disabled=bool(user.disabled) if user else False,
        last_login_at=user.last_login_at.isoformat() if user and user.last_login_at else None,
    )


def _invitation_to_view(
    invitation: MemberInvitation, inviter_emails: dict[str, str]
) -> InvitationView:
    inviter_id = str(invitation.invited_by_user_id) if invitation.invited_by_user_id else ""
    return InvitationView(
        id=str(invitation.id),
        email=invitation.email,
        role=invitation.role.value,
        state=invitation.state.value,
        invited_by_user_id=inviter_id,
        invited_by_email=inviter_emails.get(inviter_id, ""),
        expires_at=invitation.expires_at.isoformat(),
        accepted_at=invitation.accepted_at.isoformat() if invitation.accepted_at else None,
        revoked_at=invitation.revoked_at.isoformat() if invitation.revoked_at else None,
        created_at=invitation.created_at.isoformat(),
    )


def _client_ip(request: Request) -> str:
    return (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "")
        or ""
    )


def _user_agent(request: Request) -> str:
    return (request.headers.get("user-agent") or "")[:300]


# Re-export for type discoverability.
__all__ = [
    "MemberManagementService",
    "MemberView",
    "InvitationView",
    "InvitationCreationResult",
    "MemberListResult",
    "MemberActionResult",
]
