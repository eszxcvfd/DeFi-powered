"""Internationalization and timezone application service (US-047).

The bounded `I18nService` is the only place in
the product that resolves a locale or timezone
from a user and organization context, formats a
stored UTC datetime in the resolved timezone,
and parses a locale or timezone value at the
API boundary. The service is the seam that a
future story can extend with additional
languages, RTL layout, currency/number
localization, or external translation services
without redefining the API or the migration.

The service writes through the audit log from
`US-026` and the secret-safe payload helper
from `US-041` for every successful and failed
locale or timezone change.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.i18n import (
    DEFAULT_LOCALE,
    DEFAULT_TIMEZONE,
    Locale,
    LocaleUnsupported,
    TimezoneInvalid,
    format_date,
    format_datetime,
    format_time,
    normalize_search,
    parse_locale,
    parse_timezone,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditActorType,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import (
    AuditContext,
    AuditTarget,
)
from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.infrastructure.db.repositories.i18n import (
    I18nRepository,
    OrganizationLocaleRow,
    UserLocaleRow,
)

logger = logging.getLogger("livelead.i18n_service")


@dataclass(frozen=True, slots=True)
class ResolvedLocale:
    """The result of resolving a locale from a
    user and organization context."""

    locale: Locale
    source: str  # "user" | "organization" | "default"
    user_locale: str | None
    organization_default_locale: str | None


@dataclass(frozen=True, slots=True)
class ResolvedTimezone:
    """The result of resolving a timezone from a
    user and organization context."""

    timezone: str
    source: str  # "user" | "organization" | "default"
    user_timezone: str | None
    organization_default_timezone: str | None


@dataclass(frozen=True, slots=True)
class UserLocaleView:
    """The current-user locale and timezone view."""

    user_id: UUID
    organization_id: UUID
    locale: str
    timezone: str
    resolved_locale: str
    resolved_timezone: str
    locale_source: str
    timezone_source: str


@dataclass(frozen=True, slots=True)
class OrganizationLocaleView:
    """The organization default locale and
    timezone view."""

    organization_id: UUID
    default_locale: str
    default_timezone: str


class I18nServiceError(Exception):
    """Base class for `I18nService` errors."""


class I18nUnsupportedLocale(I18nServiceError):
    """Raised when a locale value is outside the
    closed set."""

    def __init__(self, value: str) -> None:
        self.value = str(value)
        self.rejection_code: str = LocaleUnsupported.rejection_code
        super().__init__(
            f"locale '{self.value}' is not in the closed set"
        )


class I18nInvalidTimezone(I18nServiceError):
    """Raised when a timezone value is not a
    valid IANA name."""

    def __init__(self, value: str) -> None:
        self.value = str(value)
        self.rejection_code: str = TimezoneInvalid.rejection_code
        super().__init__(
            f"timezone '{self.value}' is not a valid IANA name"
        )


class I18nService:
    """Bounded internationalization and timezone
    service.

    The service owns the resolution chain, the
    datetime formatting, the parsers, and the
    audit entry shape. The REST surface calls
    the service from the request handlers; the
    React UI consumes the API payload.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        audit_service: Any = None,
    ) -> None:
        self._session = session
        self._repo = I18nRepository(session)
        self._audit_service = audit_service

    @property
    def session(self) -> AsyncSession:
        return self._session

    @property
    def repository(self) -> I18nRepository:
        return self._repo

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve_locale(
        self,
        user: UserLocaleRow | None,
        organization: OrganizationLocaleRow | None,
    ) -> ResolvedLocale:
        """Resolve the effective locale for a
        user and organization.

        The fallback order is:

        1. `user.locale` if set and not empty.
        2. `organization.default_locale` if set
           and not empty.
        3. `default_locale` (`en-US`).
        """
        user_locale: str | None = None
        if user is not None:
            candidate = (user.locale or "").strip()
            if candidate:
                user_locale = candidate
        org_locale: str | None = None
        if organization is not None:
            candidate = (organization.default_locale or "").strip()
            if candidate:
                org_locale = candidate
        if user_locale:
            try:
                return ResolvedLocale(
                    locale=parse_locale(user_locale),
                    source="user",
                    user_locale=user_locale,
                    organization_default_locale=org_locale,
                )
            except LocaleUnsupported:
                pass
        if org_locale:
            try:
                return ResolvedLocale(
                    locale=parse_locale(org_locale),
                    source="organization",
                    user_locale=user_locale,
                    organization_default_locale=org_locale,
                )
            except LocaleUnsupported:
                pass
        return ResolvedLocale(
            locale=DEFAULT_LOCALE,
            source="default",
            user_locale=user_locale,
            organization_default_locale=org_locale,
        )

    def resolve_timezone(
        self,
        user: UserLocaleRow | None,
        organization: OrganizationLocaleRow | None,
    ) -> ResolvedTimezone:
        """Resolve the effective timezone for a
        user and organization.

        The fallback order is:

        1. `user.timezone` if set and not empty.
        2. `organization.default_timezone` if set
           and not empty.
        3. `default_timezone` (`UTC`).
        """
        user_timezone: str | None = None
        if user is not None:
            candidate = (user.timezone or "").strip()
            if candidate:
                user_timezone = candidate
        org_timezone: str | None = None
        if organization is not None:
            candidate = (organization.default_timezone or "").strip()
            if candidate:
                org_timezone = candidate
        if user_timezone:
            try:
                return ResolvedTimezone(
                    timezone=parse_timezone(user_timezone),
                    source="user",
                    user_timezone=user_timezone,
                    organization_default_timezone=org_timezone,
                )
            except TimezoneInvalid:
                pass
        if org_timezone:
            try:
                return ResolvedTimezone(
                    timezone=parse_timezone(org_timezone),
                    source="organization",
                    user_timezone=user_timezone,
                    organization_default_timezone=org_timezone,
                )
            except TimezoneInvalid:
                pass
        return ResolvedTimezone(
            timezone=DEFAULT_TIMEZONE,
            source="default",
            user_timezone=user_timezone,
            organization_default_timezone=org_timezone,
        )

    # ------------------------------------------------------------------
    # Parsers (re-export from domain for the API boundary)
    # ------------------------------------------------------------------

    def parse_locale(self, value: str | None) -> Locale:
        try:
            return parse_locale(value)
        except LocaleUnsupported as exc:
            raise I18nUnsupportedLocale(exc.value) from exc

    def parse_timezone(self, value: str | None) -> str:
        try:
            return parse_timezone(value)
        except TimezoneInvalid as exc:
            raise I18nInvalidTimezone(exc.value) from exc

    # ------------------------------------------------------------------
    # Formatters
    # ------------------------------------------------------------------

    def format_datetime(
        self, dt: datetime | None, locale: Locale, timezone: str
    ) -> str:
        return format_datetime(dt, locale, timezone)

    def format_date(
        self, dt: datetime | None, locale: Locale, timezone: str
    ) -> str:
        return format_date(dt, locale, timezone)

    def format_time(
        self, dt: datetime | None, locale: Locale, timezone: str
    ) -> str:
        return format_time(dt, locale, timezone)

    def normalize_search(self, value: str, locale: Locale | None = None) -> str:
        return normalize_search(value, locale)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_user_locale(
        self,
        user_id: UUID | str,
        organization_id: UUID | str,
    ) -> UserLocaleView:
        user = await self._repo.get_user(user_id, organization_id)
        organization = await self._repo.get_organization(organization_id)
        resolved_locale = self.resolve_locale(user, organization)
        resolved_timezone = self.resolve_timezone(user, organization)
        return UserLocaleView(
            user_id=UUID(str(user_id)),
            organization_id=UUID(str(organization_id)),
            locale=(user.locale if user else "") or "",
            timezone=(user.timezone if user else "") or "",
            resolved_locale=resolved_locale.locale.value,
            resolved_timezone=resolved_timezone.timezone,
            locale_source=resolved_locale.source,
            timezone_source=resolved_timezone.source,
        )

    async def get_organization_locale(
        self, organization_id: UUID | str
    ) -> OrganizationLocaleView | None:
        organization = await self._repo.get_organization(organization_id)
        if organization is None:
            return None
        return OrganizationLocaleView(
            organization_id=UUID(str(organization_id)),
            default_locale=(organization.default_locale or "") or DEFAULT_LOCALE.value,
            default_timezone=(organization.default_timezone or "") or DEFAULT_TIMEZONE,
        )

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def update_user_locale(
        self,
        *,
        user_id: UUID | str,
        organization_id: UUID | str,
        locale: str | None,
        timezone: str | None,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "",
    ) -> UserLocaleView:
        # Validate inputs
        new_locale_value: str | None = None
        new_timezone_value: str | None = None
        if locale is not None:
            try:
                parsed = self.parse_locale(locale)
                new_locale_value = parsed.value
            except I18nUnsupportedLocale as exc:
                await self._record_audit(
                    action="locale.unsupported.rejected",
                    organization_id=organization_id,
                    target_user_id=user_id,
                    payload={
                        "field": "locale",
                        "requested_value": str(exc.value)[:64],
                        "rejection_code": exc.rejection_code,
                    },
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    actor=actor,
                    actor_role=actor_role,
                )
                raise
        if timezone is not None:
            try:
                parsed = self.parse_timezone(timezone)
                new_timezone_value = parsed
            except I18nInvalidTimezone as exc:
                await self._record_audit(
                    action="locale.unsupported.rejected",
                    organization_id=organization_id,
                    target_user_id=user_id,
                    payload={
                        "field": "timezone",
                        "requested_value": str(exc.value)[:64],
                        "rejection_code": exc.rejection_code,
                    },
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    actor=actor,
                    actor_role=actor_role,
                )
                raise
        previous = await self._repo.get_user(user_id, organization_id)
        previous_locale = previous.locale if previous else ""
        previous_timezone = previous.timezone if previous else ""
        updated = await self._repo.update_user(
            user_id=user_id,
            organization_id=organization_id,
            locale=new_locale_value,
            timezone=new_timezone_value,
        )
        # Build audit entry payload
        if new_locale_value is not None and new_locale_value != previous_locale:
            await self._record_audit(
                action="user.locale.updated",
                organization_id=organization_id,
                target_user_id=user_id,
                payload={
                    "field": "locale",
                    "previous_value": str(previous_locale)[:64],
                    "new_value": str(new_locale_value)[:64],
                },
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                actor=actor,
                actor_role=actor_role,
            )
        if (
            new_timezone_value is not None
            and new_timezone_value != previous_timezone
        ):
            await self._record_audit(
                action="user.locale.updated",
                organization_id=organization_id,
                target_user_id=user_id,
                payload={
                    "field": "timezone",
                    "previous_value": str(previous_timezone)[:64],
                    "new_value": str(new_timezone_value)[:64],
                },
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                actor=actor,
                actor_role=actor_role,
            )
        return await self.get_user_locale(user_id, organization_id)

    async def update_organization_locale(
        self,
        *,
        organization_id: UUID | str,
        default_locale: str | None,
        default_timezone: str | None,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "",
    ) -> OrganizationLocaleView:
        new_locale_value: str | None = None
        new_timezone_value: str | None = None
        if default_locale is not None:
            try:
                parsed = self.parse_locale(default_locale)
                new_locale_value = parsed.value
            except I18nUnsupportedLocale as exc:
                await self._record_audit(
                    action="locale.unsupported.rejected",
                    organization_id=organization_id,
                    target_user_id=None,
                    payload={
                        "field": "default_locale",
                        "requested_value": str(exc.value)[:64],
                        "rejection_code": exc.rejection_code,
                    },
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    actor=actor,
                    actor_role=actor_role,
                )
                raise
        if default_timezone is not None:
            try:
                parsed = self.parse_timezone(default_timezone)
                new_timezone_value = parsed
            except I18nInvalidTimezone as exc:
                await self._record_audit(
                    action="locale.unsupported.rejected",
                    organization_id=organization_id,
                    target_user_id=None,
                    payload={
                        "field": "default_timezone",
                        "requested_value": str(exc.value)[:64],
                        "rejection_code": exc.rejection_code,
                    },
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    actor=actor,
                    actor_role=actor_role,
                )
                raise
        previous = await self._repo.get_organization(organization_id)
        if previous is None:
            raise I18nServiceError("organization not found")
        previous_locale = previous.default_locale or ""
        previous_timezone = previous.default_timezone or ""
        await self._repo.update_organization(
            organization_id=organization_id,
            default_locale=new_locale_value,
            default_timezone=new_timezone_value,
        )
        if new_locale_value is not None and new_locale_value != previous_locale:
            await self._record_audit(
                action="organization.locale.updated",
                organization_id=organization_id,
                target_user_id=None,
                payload={
                    "field": "default_locale",
                    "previous_value": str(previous_locale)[:64],
                    "new_value": str(new_locale_value)[:64],
                },
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                actor=actor,
                actor_role=actor_role,
            )
        if (
            new_timezone_value is not None
            and new_timezone_value != previous_timezone
        ):
            await self._record_audit(
                action="organization.locale.updated",
                organization_id=organization_id,
                target_user_id=None,
                payload={
                    "field": "default_timezone",
                    "previous_value": str(previous_timezone)[:64],
                    "new_value": str(new_timezone_value)[:64],
                },
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                actor=actor,
                actor_role=actor_role,
            )
        return await self.get_organization_locale(organization_id)

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    async def _record_audit(
        self,
        *,
        action: str,
        organization_id: UUID | str,
        target_user_id: UUID | str | None,
        payload: dict[str, Any],
        request_id: str,
        ip_address: str,
        user_agent: str,
        actor: str,
        actor_role: str,
    ) -> None:
        try:
            parsed_action = AuditAction(action)
        except ValueError:
            return
        # Sanitize payload with the helper from US-041.
        from livelead.domain.observability.sanitization import (
            sanitize_alert_payload,
        )

        safe_payload, _ = sanitize_alert_payload(payload)
        target_type = (
            AuditTargetType.USER
            if target_user_id is not None
            else AuditTargetType.SYSTEM
        )
        target_id = (
            str(target_user_id)
            if target_user_id is not None
            else str(organization_id)
        )
        target_display = (
            f"user:{target_user_id}"
            if target_user_id is not None
            else f"organization:{organization_id}"
        )
        outcome = (
            AuditOutcome.SUCCEEDED
            if parsed_action
            in (
                AuditAction.USER_LOCALE_UPDATED,
                AuditAction.ORGANIZATION_LOCALE_UPDATED,
            )
            else AuditOutcome.DENIED
        )
        try:
            await self._audit_service.emit(
                organization_id=UUID(str(organization_id)),
                actor=make_actor_from_role(
                    actor_role, actor_id=actor or None
                ),
                action=parsed_action,
                target=AuditTarget(
                    target_type=target_type,
                    target_id=target_id,
                    display=target_display,
                ),
                outcome=outcome,
                context=make_context(
                    request_id=request_id,
                    ip=ip_address,
                    user_agent=user_agent,
                    workflow="i18n",
                ),
                metadata=safe_payload,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "i18n audit record failed: action=%s err=%s",
                action,
                exc,
            )


__all__ = [
    "DEFAULT_LOCALE",
    "DEFAULT_TIMEZONE",
    "I18nInvalidTimezone",
    "I18nService",
    "I18nServiceError",
    "I18nUnsupportedLocale",
    "OrganizationLocaleView",
    "ResolvedLocale",
    "ResolvedTimezone",
    "UserLocaleView",
    "format_date",
    "format_datetime",
    "format_time",
    "normalize_search",
    "parse_locale",
    "parse_timezone",
]
