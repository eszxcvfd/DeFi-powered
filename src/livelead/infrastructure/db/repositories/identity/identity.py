"""Persistence repositories for identity and access (US-027 + US-028)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.identity import (
    InvitationState,
    MemberInvitation,
    MembershipState,
    OrganizationMembership,
    Role,
    Session,
    User,
)
from livelead.infrastructure.db.identity_mappers import (
    row_to_member_invitation,
    row_to_membership,
    row_to_session,
    row_to_user,
)
from livelead.infrastructure.db.models import (
    MemberInvitationRow,
    OrganizationMembershipRow,
    SessionRow,
    UserRow,
)


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(
            select(UserRow).where(UserRow.id == str(user_id))
        )
        row = result.scalar_one_or_none()
        return row_to_user(row) if row else None

    async def get_by_email_hash(self, email_hash: str) -> User | None:
        result = await self._session.execute(
            select(UserRow).where(UserRow.email_hash == email_hash)
        )
        row = result.scalar_one_or_none()
        return row_to_user(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserRow).where(UserRow.email == email.strip().lower())
        )
        row = result.scalar_one_or_none()
        return row_to_user(row) if row else None

    async def add(
        self,
        *,
        email: str,
        email_hash: str,
        display_name: str,
        password_hash: str,
        password_salt: str,
        password_iterations: int,
    ) -> User:
        now = datetime.now(UTC)
        row = UserRow(
            id=str(uuid4()),
            email=email.strip().lower(),
            email_hash=email_hash,
            display_name=display_name,
            password_hash=password_hash,
            password_salt=password_salt,
            password_iterations=password_iterations,
            disabled=False,
            failed_attempts=0,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_user(row)

    async def record_login(self, user_id: UUID) -> None:
        result = await self._session.execute(
            select(UserRow).where(UserRow.id == str(user_id))
        )
        row = result.scalar_one_or_none()
        if not row:
            return
        row.last_login_at = datetime.now(UTC)
        row.failed_attempts = 0
        row.locked_until = None
        row.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def record_failure(self, user_id: UUID) -> None:
        result = await self._session.execute(
            select(UserRow).where(UserRow.id == str(user_id))
        )
        row = result.scalar_one_or_none()
        if not row:
            return
        row.failed_attempts = int(row.failed_attempts or 0) + 1
        row.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def set_locked(self, user_id: UUID, until: datetime | None) -> None:
        result = await self._session.execute(
            select(UserRow).where(UserRow.id == str(user_id))
        )
        row = result.scalar_one_or_none()
        if not row:
            return
        row.locked_until = until
        row.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def set_disabled(self, user_id: UUID, disabled: bool) -> None:
        result = await self._session.execute(
            select(UserRow).where(UserRow.id == str(user_id))
        )
        row = result.scalar_one_or_none()
        if not row:
            return
        row.disabled = disabled
        row.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def count_all(self) -> int:
        from sqlalchemy import func

        result = await self._session.execute(select(func.count(UserRow.id)))
        return int(result.scalar_one() or 0)


class MembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_user(self, user_id: UUID) -> OrganizationMembership | None:
        result = await self._session.execute(
            select(OrganizationMembershipRow)
            .where(OrganizationMembershipRow.user_id == str(user_id))
            .order_by(OrganizationMembershipRow.created_at.asc())
        )
        row = result.scalars().first()
        return row_to_membership(row) if row else None

    async def list_for_organization(
        self, organization_id: UUID
    ) -> list[OrganizationMembership]:
        result = await self._session.execute(
            select(OrganizationMembershipRow)
            .where(OrganizationMembershipRow.organization_id == str(organization_id))
            .order_by(OrganizationMembershipRow.created_at.asc())
        )
        return [row_to_membership(r) for r in result.scalars().all()]

    async def get_active_for_user(
        self, user_id: UUID
    ) -> OrganizationMembership | None:
        result = await self._session.execute(
            select(OrganizationMembershipRow)
            .where(
                and_(
                    OrganizationMembershipRow.user_id == str(user_id),
                    OrganizationMembershipRow.state == MembershipState.ACTIVE.value,
                )
            )
            .order_by(OrganizationMembershipRow.created_at.asc())
        )
        row = result.scalars().first()
        return row_to_membership(row) if row else None

    async def get_active_membership(
        self, organization_id: UUID, user_id: UUID
    ) -> OrganizationMembership | None:
        result = await self._session.execute(
            select(OrganizationMembershipRow)
            .where(
                and_(
                    OrganizationMembershipRow.user_id == str(user_id),
                    OrganizationMembershipRow.organization_id == str(organization_id),
                    OrganizationMembershipRow.state == MembershipState.ACTIVE.value,
                )
            )
        )
        row = result.scalars().first()
        return row_to_membership(row) if row else None

    async def get_for_user_and_org(
        self, organization_id: UUID, user_id: UUID
    ) -> OrganizationMembership | None:
        result = await self._session.execute(
            select(OrganizationMembershipRow)
            .where(
                and_(
                    OrganizationMembershipRow.user_id == str(user_id),
                    OrganizationMembershipRow.organization_id == str(organization_id),
                )
            )
        )
        row = result.scalars().first()
        return row_to_membership(row) if row else None

    async def get_for_id(
        self, organization_id: UUID, membership_id: UUID
    ) -> OrganizationMembership | None:
        result = await self._session.execute(
            select(OrganizationMembershipRow)
            .where(
                and_(
                    OrganizationMembershipRow.id == str(membership_id),
                    OrganizationMembershipRow.organization_id == str(organization_id),
                )
            )
        )
        row = result.scalars().first()
        return row_to_membership(row) if row else None

    async def get_by_email(
        self, organization_id: UUID, email: str
    ) -> OrganizationMembership | None:
        """Find a membership by joining through the users table.

        Memberships reference user ids, not emails, so a join is required.
        The match is on the normalized lower-case email column.
        """

        from livelead.infrastructure.db.models import UserRow as _UserRow

        result = await self._session.execute(
            select(OrganizationMembershipRow)
            .join(_UserRow, _UserRow.id == OrganizationMembershipRow.user_id)
            .where(
                and_(
                    OrganizationMembershipRow.organization_id == str(organization_id),
                    _UserRow.email == email.strip().lower(),
                )
            )
            .order_by(OrganizationMembershipRow.created_at.asc())
        )
        row = result.scalars().first()
        return row_to_membership(row) if row else None

    async def set_state(
        self, organization_id: UUID, membership_id: UUID, state: MembershipState
    ) -> None:
        result = await self._session.execute(
            select(OrganizationMembershipRow)
            .where(
                and_(
                    OrganizationMembershipRow.id == str(membership_id),
                    OrganizationMembershipRow.organization_id == str(organization_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return
        row.state = state.value
        row.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def set_role(
        self, organization_id: UUID, membership_id: UUID, role: Role
    ) -> None:
        result = await self._session.execute(
            select(OrganizationMembershipRow)
            .where(
                and_(
                    OrganizationMembershipRow.id == str(membership_id),
                    OrganizationMembershipRow.organization_id == str(organization_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return
        row.role = role.value
        row.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def add(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        role: Role,
        state: MembershipState = MembershipState.ACTIVE,
    ) -> OrganizationMembership:
        now = datetime.now(UTC)
        row = OrganizationMembershipRow(
            id=str(uuid4()),
            user_id=str(user_id),
            organization_id=str(organization_id),
            role=role.value,
            state=state.value,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_membership(row)


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, session: Session) -> Session:
        row = SessionRow(
            id=str(session.id),
            user_id=str(session.user_id),
            organization_id=str(session.organization_id),
            role=session.role.value,
            token_hash=session.token_hash,
            issued_at=session.issued_at,
            expires_at=session.expires_at,
            last_seen_at=session.last_seen_at,
            rotated_at=session.rotated_at,
            revoked_at=session.revoked_at,
            client_ip=session.client_ip or "",
            user_agent=(session.user_agent or "")[:300],
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_session(row)

    async def get_by_token_hash(self, token_hash: str) -> Session | None:
        result = await self._session.execute(
            select(SessionRow).where(SessionRow.token_hash == token_hash)
        )
        row = result.scalar_one_or_none()
        return row_to_session(row) if row else None

    async def get_for_user(self, session_id: UUID, user_id: UUID) -> Session | None:
        result = await self._session.execute(
            select(SessionRow).where(
                and_(
                    SessionRow.id == str(session_id),
                    SessionRow.user_id == str(user_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        return row_to_session(row) if row else None

    async def touch(self, session_id: UUID) -> None:
        result = await self._session.execute(
            select(SessionRow).where(SessionRow.id == str(session_id))
        )
        row = result.scalar_one_or_none()
        if not row:
            return
        row.last_seen_at = datetime.now(UTC)
        await self._session.flush()

    async def revoke(self, session_id: UUID) -> None:
        result = await self._session.execute(
            select(SessionRow).where(SessionRow.id == str(session_id))
        )
        row = result.scalar_one_or_none()
        if not row or row.revoked_at is not None:
            return
        row.revoked_at = datetime.now(UTC)
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        result = await self._session.execute(
            select(SessionRow).where(
                and_(
                    SessionRow.user_id == str(user_id),
                    SessionRow.revoked_at.is_(None),
                )
            )
        )
        rows = list(result.scalars().all())
        for row in rows:
            row.revoked_at = datetime.now(UTC)
        await self._session.flush()
        return len(rows)

    async def revoke_all_for_user_and_org(
        self, user_id: UUID, organization_id: UUID
    ) -> int:
        result = await self._session.execute(
            select(SessionRow).where(
                and_(
                    SessionRow.user_id == str(user_id),
                    SessionRow.organization_id == str(organization_id),
                    SessionRow.revoked_at.is_(None),
                )
            )
        )
        rows = list(result.scalars().all())
        for row in rows:
            row.revoked_at = datetime.now(UTC)
        await self._session.flush()
        return len(rows)


class MemberInvitationRepository:
    """Repository for member invitations (US-028)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        organization_id: UUID,
        email: str,
        role: Role,
        state: InvitationState,
        token_hash: str,
        invited_by_user_id: UUID | None,
        expires_at: datetime,
    ) -> MemberInvitation:
        now = datetime.now(UTC)
        row = MemberInvitationRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            email=email.strip().lower(),
            role=role.value,
            state=state.value,
            token_hash=token_hash,
            invited_by_user_id=str(invited_by_user_id) if invited_by_user_id else None,
            expires_at=expires_at,
            accepted_at=None,
            accepted_by_user_id=None,
            revoked_at=None,
            revoked_by_user_id=None,
            revoke_reason=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_member_invitation(row)

    async def get_by_token_hash(self, token_hash: str) -> MemberInvitation | None:
        result = await self._session.execute(
            select(MemberInvitationRow).where(
                MemberInvitationRow.token_hash == token_hash
            )
        )
        row = result.scalar_one_or_none()
        return row_to_member_invitation(row) if row else None

    async def get_for_org(
        self, organization_id: UUID, invitation_id: UUID
    ) -> MemberInvitation | None:
        result = await self._session.execute(
            select(MemberInvitationRow).where(
                and_(
                    MemberInvitationRow.id == str(invitation_id),
                    MemberInvitationRow.organization_id == str(organization_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        return row_to_member_invitation(row) if row else None

    async def list_for_org(
        self,
        organization_id: UUID,
        *,
        states: list[InvitationState] | None = None,
    ) -> list[MemberInvitation]:
        stmt = select(MemberInvitationRow).where(
            MemberInvitationRow.organization_id == str(organization_id)
        )
        if states:
            stmt = stmt.where(
                MemberInvitationRow.state.in_([s.value for s in states])
            )
        stmt = stmt.order_by(MemberInvitationRow.created_at.desc())
        result = await self._session.execute(stmt)
        return [row_to_member_invitation(r) for r in result.scalars().all()]

    async def list_pending_for_email(
        self, email: str
    ) -> list[MemberInvitation]:
        """Return all pending invitations for a given email across orgs.

        Used at acceptance time to match an incoming email to the
        invitations it can redeem. The state filter keeps the result
        list narrow to the redeemable set.
        """

        result = await self._session.execute(
            select(MemberInvitationRow)
            .where(
                and_(
                    MemberInvitationRow.email == email.strip().lower(),
                    or_(
                        MemberInvitationRow.state == InvitationState.PENDING.value,
                    ),
                )
            )
            .order_by(MemberInvitationRow.created_at.desc())
        )
        return [row_to_member_invitation(r) for r in result.scalars().all()]

    async def set_state(
        self,
        invitation_id: UUID,
        state: InvitationState,
        *,
        accepted_by_user_id: UUID | None = None,
        accepted_at: datetime | None = None,
        revoked_by_user_id: UUID | None = None,
        revoked_at: datetime | None = None,
        revoke_reason: str | None = None,
    ) -> MemberInvitation | None:
        result = await self._session.execute(
            select(MemberInvitationRow).where(
                MemberInvitationRow.id == str(invitation_id)
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        row.state = state.value
        if accepted_by_user_id is not None:
            row.accepted_by_user_id = str(accepted_by_user_id)
        if accepted_at is not None:
            row.accepted_at = accepted_at
        if revoked_by_user_id is not None:
            row.revoked_by_user_id = str(revoked_by_user_id)
        if revoked_at is not None:
            row.revoked_at = revoked_at
        if revoke_reason is not None:
            row.revoke_reason = revoke_reason
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return row_to_member_invitation(row)


__all__ = [
    "UserRepository",
    "MembershipRepository",
    "SessionRepository",
    "MemberInvitationRepository",
]
