"""Internationalization and timezone repository (US-047).

The repository owns every read and write for
the `users.locale`, `users.timezone`,
`organizations.default_locale`, and
`organizations.default_timezone` columns. All
methods take `organization_id` first so tenant
isolation is mandatory at the data layer. The
repository deliberately returns light dataclasses
that the application service consumes; the
`I18nService` is the only place that knows the
secret-safe payload contract and the audit entry
shape.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.infrastructure.db.models import (
    OrganizationRow,
    UserRow,
)

logger = logging.getLogger("livelead.i18n_repo")


@dataclass(frozen=True, slots=True)
class UserLocaleRow:
    """Light read model for a user locale and
    timezone row.

    The repository returns this dataclass so the
    application service can resolve the effective
    locale and timezone without reading the full
    user record.
    """

    id: str
    organization_id: str | None
    locale: str
    timezone: str


@dataclass(frozen=True, slots=True)
class OrganizationLocaleRow:
    """Light read model for an organization
    default locale and timezone row.
    """

    id: str
    default_locale: str
    default_timezone: str


def _uuid(value: UUID | str | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _row_to_user_locale(row: UserRow | None) -> UserLocaleRow | None:
    if row is None:
        return None
    return UserLocaleRow(
        id=str(row.id),
        organization_id=None,
        locale=str(row.locale or ""),
        timezone=str(row.timezone or ""),
    )


def _row_to_organization_locale(
    row: OrganizationRow | None,
) -> OrganizationLocaleRow | None:
    if row is None:
        return None
    return OrganizationLocaleRow(
        id=str(row.id),
        default_locale=str(row.default_locale or ""),
        default_timezone=str(row.default_timezone or ""),
    )


class I18nRepository:
    """Reads and writes for the i18n columns."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def get_user(
        self,
        user_id: UUID | str,
        organization_id: UUID | str | None = None,
    ) -> UserLocaleRow | None:
        stmt = select(UserRow).where(UserRow.id == str(user_id))
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _row_to_user_locale(row)

    async def get_organization(
        self, organization_id: UUID | str
    ) -> OrganizationLocaleRow | None:
        stmt = select(OrganizationRow).where(
            OrganizationRow.id == str(organization_id)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _row_to_organization_locale(row)

    async def update_user(
        self,
        *,
        user_id: UUID | str,
        organization_id: UUID | str,
        locale: str | None,
        timezone: str | None,
    ) -> UserLocaleRow | None:
        stmt = select(UserRow).where(UserRow.id == str(user_id))
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        if locale is not None:
            row.locale = str(locale)
        if timezone is not None:
            row.timezone = str(timezone)
        await self._session.flush()
        return _row_to_user_locale(row)

    async def update_organization(
        self,
        *,
        organization_id: UUID | str,
        default_locale: str | None,
        default_timezone: str | None,
    ) -> OrganizationLocaleRow | None:
        stmt = select(OrganizationRow).where(
            OrganizationRow.id == str(organization_id)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        if default_locale is not None:
            row.default_locale = str(default_locale)
        if default_timezone is not None:
            row.default_timezone = str(default_timezone)
        await self._session.flush()
        return _row_to_organization_locale(row)


__all__ = [
    "I18nRepository",
    "OrganizationLocaleRow",
    "UserLocaleRow",
]
