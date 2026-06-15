"""Member management REST surface (US-028)."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.member_management import (
    InvitationView,
    MemberActionResult,
    MemberListResult,
    MemberManagementService,
    MemberView,
)
from livelead.domain.identity import (
    AuthenticatedIdentity,
    MemberManagementError,
    Role,
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
    parse_role,
)
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
)
from livelead.interfaces.rest.auth import _set_session_cookie
from livelead.interfaces.rest.deps import get_db_session

logger = logging.getLogger("livelead.member_api")

router = APIRouter(prefix="/admin/members", tags=["members"])
invite_router = APIRouter(prefix="/auth/invitations", tags=["invitations"])


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------
class InvitationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: str = Field(min_length=2, max_length=32)


class InvitationRevokeRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


class RoleChangeRequest(BaseModel):
    role: str = Field(min_length=2, max_length=32)


class InvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=8, max_length=512)
    password: str = Field(min_length=12, max_length=256)
    display_name: str | None = Field(default=None, max_length=200)


class MemberSchema(BaseModel):
    id: str
    user_id: str
    email: str
    display_name: str
    role: str
    state: str
    created_at: str
    updated_at: str
    disabled: bool
    last_login_at: str | None = None


class InvitationSchema(BaseModel):
    id: str
    email: str
    role: str
    state: str
    invited_by_user_id: str
    invited_by_email: str
    expires_at: str
    accepted_at: str | None = None
    revoked_at: str | None = None
    created_at: str


class MemberListResponse(BaseModel):
    members: list[MemberSchema]
    invitations: list[InvitationSchema]
    total_members: int
    total_invitations: int


class InvitationCreateResponse(BaseModel):
    invitation: InvitationSchema
    invite_token: str
    invite_url: str | None = None
    expires_at: str


class MemberActionResponse(BaseModel):
    member: MemberSchema
    sessions_revoked: int = 0


class InvitationActionResponse(BaseModel):
    invitation: InvitationSchema


class AcceptResponse(BaseModel):
    user_id: str
    membership_id: str
    role: str
    organization_id: str
    new_user: bool
    expires_in: int


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _identity_from_tenant(tenant: TenantContext) -> AuthenticatedIdentity:
    if not tenant.is_authenticated() or tenant.session_id is None:
        raise HTTPException(status_code=401, detail="authentication required")
    if tenant.role is None:
        raise HTTPException(status_code=403, detail="role required")
    return AuthenticatedIdentity(
        user_id=UUID(tenant.actor_id),
        email=tenant.email,
        display_name=tenant.display_name,
        organization_id=tenant.organization_id,
        role=tenant.role,
        session_id=tenant.session_id,
        expires_at=None,  # type: ignore[arg-type]
    )


def _require_governance(tenant: TenantContext) -> AuthenticatedIdentity:
    identity = _identity_from_tenant(tenant)
    if identity.role not in (Role.OWNER, Role.ADMIN):
        raise HTTPException(status_code=403, detail="governance role required")
    return identity


def _parse_role(value: str) -> Role:
    role = parse_role(value)
    if role is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": MemberManagementError.INVALID_PAYLOAD,
                "message": f"unknown role: {value}",
            },
        )
    if role in (Role.OWNER,):
        # Owner-level invitations are allowed only for owners. The
        # governance matrix in `can_manage_member_governance` will still
        # reject them when the actor is an admin, so we accept the value
        # here to give a clean error from the service.
        pass
    return role


def _member_view(m: MemberView) -> MemberSchema:
    return MemberSchema(
        id=m.id,
        user_id=m.user_id,
        email=m.email,
        display_name=m.display_name,
        role=m.role,
        state=m.state,
        created_at=m.created_at,
        updated_at=m.updated_at,
        disabled=m.disabled,
        last_login_at=m.last_login_at,
    )


def _invitation_view(v: InvitationView) -> InvitationSchema:
    return InvitationSchema(
        id=v.id,
        email=v.email,
        role=v.role,
        state=v.state,
        invited_by_user_id=v.invited_by_user_id,
        invited_by_email=v.invited_by_email,
        expires_at=v.expires_at,
        accepted_at=v.accepted_at,
        revoked_at=v.revoked_at,
        created_at=v.created_at,
    )


def _map_blocked(public_reason: str, detail: str | None = None) -> HTTPException:
    if public_reason in (
        MemberManagementError.LAST_OWNER_PROTECTED,
        MemberManagementError.ROLE_NOT_GOVERNABLE,
        MemberManagementError.EMAIL_ALREADY_MEMBER,
    ):
        status_code = 409
    elif public_reason in (
        MemberManagementError.FORBIDDEN,
    ):
        status_code = 403
    elif public_reason in (
        MemberManagementError.INVITE_EXPIRED,
        MemberManagementError.INVITE_REVOKED,
        MemberManagementError.INVITE_ALREADY_ACCEPTED,
    ):
        status_code = 410
    elif public_reason == MemberManagementError.NOT_FOUND:
        status_code = 404
    elif public_reason == MemberManagementError.INVALID_PAYLOAD:
        status_code = 400
    else:
        status_code = 409
    return HTTPException(
        status_code=status_code,
        detail={"code": public_reason, "message": detail or public_reason},
    )


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@router.get("", response_model=MemberListResponse)
async def list_members(
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> MemberListResponse:
    identity = _require_governance(tenant)
    svc = MemberManagementService(session)
    result: MemberListResult = await svc.list_organization_members(
        organization_id=identity.organization_id
    )
    await session.commit()
    return MemberListResponse(
        members=[_member_view(m) for m in result.members],
        invitations=[_invitation_view(v) for v in result.invitations],
        total_members=result.total_members,
        total_invitations=result.total_invitations,
    )


@router.post(
    "/invitations",
    response_model=InvitationCreateResponse,
    status_code=201,
)
async def create_invitation(
    body: InvitationRequest,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> InvitationCreateResponse:
    identity = _require_governance(tenant)
    role = _parse_role(body.role)
    svc = MemberManagementService(session)
    outcome, public_reason, _ = await svc.invite_member(
        request=request,
        organization_id=identity.organization_id,
        actor=identity,
        email=body.email,
        role=role,
    )
    if outcome is None or outcome.invite_token is None:
        raise _map_blocked(public_reason or MemberManagementError.INVALID_STATE)
    # Build a one-shot response that exposes the cleartext token to the
    # operator. The persisted row only stores the token_hash, so this
    # value cannot be retrieved again.
    listing = await svc.list_organization_members(
        organization_id=identity.organization_id
    )
    new_invite = next(
        (i for i in listing.invitations if i.email == body.email.strip().lower()),
        None,
    )
    if new_invite is None:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail="invitation not visible after create")
    return InvitationCreateResponse(
        invitation=_invitation_view(new_invite),
        invite_token=outcome.invite_token,
        invite_url=f"/invitations/accept?token={outcome.invite_token}",
        expires_at=new_invite.expires_at,
    )


@router.post(
    "/invitations/{invitation_id}/revoke",
    response_model=InvitationActionResponse,
)
async def revoke_invitation(
    invitation_id: UUID,
    request: Request,
    body: InvitationRevokeRequest | None = None,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> InvitationActionResponse:
    identity = _require_governance(tenant)
    svc = MemberManagementService(session)
    view, public_reason, _ = await svc.revoke_invitation(
        request=request,
        organization_id=identity.organization_id,
        actor=identity,
        invitation_id=invitation_id,
        reason=body.reason if body else None,
    )
    if view is None:
        raise _map_blocked(public_reason or MemberManagementError.INVALID_STATE)
    return InvitationActionResponse(invitation=_invitation_view(view))


@router.patch(
    "/{membership_id}",
    response_model=MemberActionResponse,
)
async def change_member(
    membership_id: UUID,
    body: RoleChangeRequest,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> MemberActionResponse:
    identity = _require_governance(tenant)
    new_role = _parse_role(body.role)
    svc = MemberManagementService(session)
    outcome, public_reason, _ = await svc.change_member_role(
        request=request,
        organization_id=identity.organization_id,
        actor=identity,
        membership_id=membership_id,
        new_role=new_role,
    )
    if outcome is None:
        raise _map_blocked(public_reason or MemberManagementError.INVALID_STATE)
    return MemberActionResponse(
        member=_member_view(outcome.member),
        sessions_revoked=outcome.sessions_revoked,
    )


@router.post(
    "/{membership_id}/disable",
    response_model=MemberActionResponse,
)
async def disable_member(
    membership_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> MemberActionResponse:
    identity = _require_governance(tenant)
    svc = MemberManagementService(session)
    outcome, public_reason, _ = await svc.disable_member(
        request=request,
        organization_id=identity.organization_id,
        actor=identity,
        membership_id=membership_id,
    )
    if outcome is None:
        raise _map_blocked(public_reason or MemberManagementError.INVALID_STATE)
    return MemberActionResponse(
        member=_member_view(outcome.member),
        sessions_revoked=outcome.sessions_revoked,
    )


@router.post(
    "/{membership_id}/enable",
    response_model=MemberActionResponse,
)
async def enable_member(
    membership_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> MemberActionResponse:
    identity = _require_governance(tenant)
    svc = MemberManagementService(session)
    outcome, public_reason, _ = await svc.enable_member(
        request=request,
        organization_id=identity.organization_id,
        actor=identity,
        membership_id=membership_id,
    )
    if outcome is None:
        raise _map_blocked(public_reason or MemberManagementError.INVALID_STATE)
    return MemberActionResponse(
        member=_member_view(outcome.member),
        sessions_revoked=outcome.sessions_revoked,
    )


@router.delete(
    "/{membership_id}",
    response_model=MemberActionResponse,
)
async def revoke_member(
    membership_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> MemberActionResponse:
    identity = _require_governance(tenant)
    svc = MemberManagementService(session)
    outcome, public_reason, _ = await svc.revoke_member_access(
        request=request,
        organization_id=identity.organization_id,
        actor=identity,
        membership_id=membership_id,
    )
    if outcome is None:
        raise _map_blocked(public_reason or MemberManagementError.INVALID_STATE)
    return MemberActionResponse(
        member=_member_view(outcome.member),
        sessions_revoked=outcome.sessions_revoked,
    )


# ----------------------------------------------------------------------
# Invitation acceptance (public to the invitee)
# ----------------------------------------------------------------------
@invite_router.post("/accept", response_model=AcceptResponse)
async def accept_invitation(
    body: InvitationAcceptRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> AcceptResponse:
    svc = MemberManagementService(session)
    result, public_reason, _ = await svc.accept_invitation(
        request=request,
        token=body.token,
        password=body.password,
        display_name=body.display_name,
    )
    if result is None:
        raise _map_blocked(public_reason or MemberManagementError.INVALID_STATE)

    if result.access_token and result.session_expires_at:
        expires_in = max(60, int((result.session_expires_at - _now()).total_seconds()))
        _set_session_cookie(response, result.access_token, expires_in)
    else:
        expires_in = SESSION_TTL_SECONDS

    return AcceptResponse(
        user_id=str(result.user_id),
        membership_id=str(result.membership_id),
        role=result.role.value,
        organization_id=str(result.organization_id),
        new_user=result.new_user,
        expires_in=expires_in,
    )


def _now():
    from datetime import UTC, datetime

    return datetime.now(UTC)


__all__ = ["router", "invite_router"]
