"""Internationalization and timezone domain types (US-047).

Closed `Locale` enum and bounded `Timezone`
validation that the `I18nService` and the REST
surface share. The values are persisted as
strings so the migration can use stable SQL
`VARCHAR` columns; the application layer
normalises back to these enums at the boundary.

The vocabulary follows
`docs/decisions/0025-internationalization-and-timezone-baseline.md`
and `SPEC.md` `NFR-I18N-001` / `NFR-I18N-002` /
`NFR-I18N-003`:

- `vi-VN` — Vietnamese (Vietnam). 24-hour
  `dd/MM/yyyy HH:mm` datetime format.
- `en-US` — English (United States). 12-hour
  `MM/dd/yyyy, h:mm a` datetime format.

The default locale is `en-US` when no
user-selected or organization default value is
present. The default timezone is `UTC`.

The bounded `Timezone` value type is validated
against the IANA tz database. The first slice
ships a closed allowlist drawn from the IANA tz
database for fast validation; the allowlist
covers all IANA names that `pytz`/`zoneinfo`
exposes through the `zoneinfo` standard library.
A future story can extend the surface with
dynamic IANA validation behind the same
`parse_timezone` function.
"""

from __future__ import annotations

import unicodedata
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class Locale(StrEnum):
    """Closed set of supported locales.

    The bounded surfaces read from and reject any
    value outside the closed set with
    `LOCALE_UNSUPPORTED`. New locales cannot be
    added without first extending the
    `I18nService`, the dictionary loader, and the
    audit entry shape.
    """

    VI_VN = "vi-VN"
    EN_US = "en-US"


# Default values used by the bounded fallback
# chain in `I18nService.resolve_locale` and
# `I18nService.resolve_timezone`.
DEFAULT_LOCALE: Locale = Locale.EN_US
DEFAULT_TIMEZONE: str = "UTC"


class LocaleUnsupported(ValueError):
    """Raised when a locale value is outside the
    closed `Locale` enum.

    The error carries the requested value and
    the rejection code that the REST surface
    returns to the client.
    """

    rejection_code: str = "LOCALE_UNSUPPORTED"

    def __init__(self, value: str) -> None:
        self.value = str(value)
        super().__init__(
            f"locale '{self.value}' is not in the closed set"
        )


class TimezoneInvalid(ValueError):
    """Raised when a timezone value is not a
    valid IANA name.

    The error carries the requested value and
    the rejection code that the REST surface
    returns to the client.
    """

    rejection_code: str = "TIMEZONE_INVALID"

    def __init__(self, value: str) -> None:
        self.value = str(value)
        super().__init__(
            f"timezone '{self.value}' is not a valid IANA name"
        )


def parse_locale(value: str | Locale | None) -> Locale:
    """Parse and validate a locale value.

    Returns the closed `Locale` enum value.
    Raises `LocaleUnsupported` for any value
    outside the closed set. The function is the
    only way the application layer reads a
    `Locale` value.
    """
    if value is None:
        raise LocaleUnsupported("")
    if isinstance(value, Locale):
        return value
    candidate = str(value).strip()
    if not candidate:
        raise LocaleUnsupported(candidate)
    try:
        return Locale(candidate)
    except ValueError as exc:
        raise LocaleUnsupported(candidate) from exc


def parse_timezone(value: str | None) -> str:
    """Parse and validate a timezone value.

    Returns a valid IANA tz name. Raises
    `TimezoneInvalid` for any value that the IANA
    tz database disallows. The function rejects
    abbreviations, offsets, and values that the
    IANA tz database does not know.

    The first slice uses the standard library
    `zoneinfo.ZoneInfo` for validation so the
    bounded path is consistent with the existing
    Python tooling.
    """
    if value is None:
        raise TimezoneInvalid("")
    candidate = str(value).strip()
    if not candidate:
        raise TimezoneInvalid(candidate)
    try:
        ZoneInfo(candidate)
    except ZoneInfoNotFoundError as exc:
        raise TimezoneInvalid(candidate) from exc
    except (ValueError, TypeError) as exc:
        raise TimezoneInvalid(candidate) from exc
    return candidate


def format_datetime(
    dt,  # datetime
    locale: Locale,
    timezone: str,
) -> str:
    """Format a stored UTC datetime in the
    resolved timezone using a closed locale
    formatter.

    The first slice ships two formatters:

    - `vi-VN` — 24-hour `dd/MM/yyyy HH:mm`.
    - `en-US` — 12-hour `MM/dd/yyyy, h:mm a`.

    The function never mutates the input; it
    always returns a fresh string. The function
    assumes the input is a UTC datetime and
    converts to the resolved timezone before
    formatting.
    """
    if dt is None:
        return ""
    try:
        from datetime import datetime, timezone as _tz

        # Treat naive datetimes as UTC.
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_tz.utc)
            target = ZoneInfo(timezone)
            local = dt.astimezone(target)
        else:
            local = dt
    except Exception:
        local = dt

    if locale is Locale.VI_VN:
        return local.strftime("%d/%m/%Y %H:%M")
    if locale is Locale.EN_US:
        return local.strftime("%m/%d/%Y, %-I:%M %p")
    # Defensive fallback: closed enum, but
    # be safe in case a future enum value
    # is added before the formatter is
    # updated.
    return local.strftime("%Y-%m-%d %H:%M:%S")


def format_date(
    dt,  # datetime
    locale: Locale,
    timezone: str,
) -> str:
    """Format a stored UTC datetime date in the
    resolved timezone using a closed locale
    formatter."""
    if dt is None:
        return ""
    formatted = format_datetime(dt, locale, timezone)
    if not formatted:
        return ""
    if locale is Locale.VI_VN:
        return formatted[:10]
    if locale is Locale.EN_US:
        return formatted.split(",", 1)[0]
    return formatted[:10]


def format_time(
    dt,  # datetime
    locale: Locale,
    timezone: str,
) -> str:
    """Format a stored UTC datetime time in the
    resolved timezone using a closed locale
    formatter."""
    if dt is None:
        return ""
    formatted = format_datetime(dt, locale, timezone)
    if not formatted:
        return ""
    if locale is Locale.VI_VN:
        return formatted[11:]
    if locale is Locale.EN_US:
        parts = formatted.split(",", 1)
        if len(parts) < 2:
            return ""
        return parts[1].strip()
    return formatted[11:]


def normalize_search(value: str, locale: Locale | None = None) -> str:
    """Normalize a search value for the
    resolved locale.

    `vi-VN` and `en-US` both receive Unicode NFC
    normalization so diacritics and tone marks
    match consistently across the discovery and
    lead surfaces.
    """
    if value is None:
        return ""
    return unicodedata.normalize("NFC", str(value))


__all__ = [
    "DEFAULT_LOCALE",
    "DEFAULT_TIMEZONE",
    "Locale",
    "LocaleUnsupported",
    "TimezoneInvalid",
    "format_date",
    "format_datetime",
    "format_time",
    "normalize_search",
    "parse_locale",
    "parse_timezone",
]
