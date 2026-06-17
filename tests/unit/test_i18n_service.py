"""Unit tests for the `I18nService` (US-047).

Covers the bounded resolution chain, the
closed `Locale` enum, the bounded `Timezone`
IANA validation, the parsers, the formatters,
and the Unicode normalization for `vi-VN`
search queries.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from livelead.application.i18n import (
    I18nInvalidTimezone,
    I18nService,
    I18nUnsupportedLocale,
    OrganizationLocaleView,
    ResolvedLocale,
    ResolvedTimezone,
    UserLocaleView,
)
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


# ---------------------------------------------------------------------------
# Closed Locale enum
# ---------------------------------------------------------------------------


def test_parse_locale_vi_vn_returns_enum() -> None:
    assert parse_locale("vi-VN") is Locale.VI_VN


def test_parse_locale_en_us_returns_enum() -> None:
    assert parse_locale("en-US") is Locale.EN_US


def test_parse_locale_unsupported_raises() -> None:
    with pytest.raises(LocaleUnsupported) as exc:
        parse_locale("fr-FR")
    assert exc.value.rejection_code == "LOCALE_UNSUPPORTED"


def test_parse_locale_empty_raises() -> None:
    with pytest.raises(LocaleUnsupported):
        parse_locale("")


def test_parse_locale_none_raises() -> None:
    with pytest.raises(LocaleUnsupported):
        parse_locale(None)


def test_parse_locale_case_sensitive() -> None:
    with pytest.raises(LocaleUnsupported):
        parse_locale("vi-vn")


# ---------------------------------------------------------------------------
# Bounded Timezone validation
# ---------------------------------------------------------------------------


def test_parse_timezone_utc_returns_value() -> None:
    assert parse_timezone("UTC") == "UTC"


def test_parse_timezone_iana_returns_value() -> None:
    assert parse_timezone("Asia/Ho_Chi_Minh") == "Asia/Ho_Chi_Minh"


def test_parse_timezone_invalid_raises() -> None:
    with pytest.raises(TimezoneInvalid) as exc:
        parse_timezone("Not/AZone")
    assert exc.value.rejection_code == "TIMEZONE_INVALID"


def test_parse_timezone_offset_rejected() -> None:
    with pytest.raises(TimezoneInvalid):
        parse_timezone("+07:00")


def test_parse_timezone_empty_raises() -> None:
    with pytest.raises(TimezoneInvalid):
        parse_timezone("")


def test_parse_timezone_none_raises() -> None:
    with pytest.raises(TimezoneInvalid):
        parse_timezone(None)


# ---------------------------------------------------------------------------
# Resolution chain
# ---------------------------------------------------------------------------


class _StubUser:
    def __init__(self, locale: str = "", timezone: str = "") -> None:
        self.locale = locale
        self.timezone = timezone


class _StubOrganization:
    def __init__(
        self, default_locale: str = "", default_timezone: str = ""
    ) -> None:
        self.default_locale = default_locale
        self.default_timezone = default_timezone


def test_resolve_locale_user_wins() -> None:
    svc = I18nService.__new__(I18nService)
    user = _StubUser(locale="vi-VN", timezone="Asia/Ho_Chi_Minh")
    org = _StubOrganization(
        default_locale="en-US", default_timezone="UTC"
    )
    result = svc.resolve_locale(user, org)
    assert isinstance(result, ResolvedLocale)
    assert result.locale is Locale.VI_VN
    assert result.source == "user"


def test_resolve_locale_organization_fallback() -> None:
    svc = I18nService.__new__(I18nService)
    user = _StubUser(locale="", timezone="")
    org = _StubOrganization(
        default_locale="vi-VN", default_timezone="Asia/Ho_Chi_Minh"
    )
    result = svc.resolve_locale(user, org)
    assert result.locale is Locale.VI_VN
    assert result.source == "organization"


def test_resolve_locale_default_fallback() -> None:
    svc = I18nService.__new__(I18nService)
    user = _StubUser(locale="", timezone="")
    org = _StubOrganization(default_locale="", default_timezone="")
    result = svc.resolve_locale(user, org)
    assert result.locale is DEFAULT_LOCALE
    assert result.source == "default"


def test_resolve_locale_user_invalid_falls_back() -> None:
    svc = I18nService.__new__(I18nService)
    user = _StubUser(locale="fr-FR", timezone="UTC")
    org = _StubOrganization(default_locale="vi-VN", default_timezone="")
    result = svc.resolve_locale(user, org)
    assert result.locale is Locale.VI_VN
    assert result.source == "organization"


def test_resolve_timezone_user_wins() -> None:
    svc = I18nService.__new__(I18nService)
    user = _StubUser(locale="", timezone="Asia/Ho_Chi_Minh")
    org = _StubOrganization(
        default_locale="en-US", default_timezone="UTC"
    )
    result = svc.resolve_timezone(user, org)
    assert isinstance(result, ResolvedTimezone)
    assert result.timezone == "Asia/Ho_Chi_Minh"
    assert result.source == "user"


def test_resolve_timezone_organization_fallback() -> None:
    svc = I18nService.__new__(I18nService)
    user = _StubUser(locale="", timezone="")
    org = _StubOrganization(
        default_locale="en-US", default_timezone="Asia/Ho_Chi_Minh"
    )
    result = svc.resolve_timezone(user, org)
    assert result.timezone == "Asia/Ho_Chi_Minh"
    assert result.source == "organization"


def test_resolve_timezone_default_fallback() -> None:
    svc = I18nService.__new__(I18nService)
    user = _StubUser(locale="", timezone="")
    org = _StubOrganization(default_locale="", default_timezone="")
    result = svc.resolve_timezone(user, org)
    assert result.timezone == DEFAULT_TIMEZONE
    assert result.source == "default"


def test_resolve_timezone_user_invalid_falls_back() -> None:
    svc = I18nService.__new__(I18nService)
    user = _StubUser(locale="", timezone="Not/AZone")
    org = _StubOrganization(
        default_locale="en-US", default_timezone="Asia/Ho_Chi_Minh"
    )
    result = svc.resolve_timezone(user, org)
    assert result.timezone == "Asia/Ho_Chi_Minh"
    assert result.source == "organization"


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def test_format_datetime_vi_vn_24h() -> None:
    dt = datetime(2026, 6, 16, 9, 30, tzinfo=timezone.utc)
    out = format_datetime(dt, Locale.VI_VN, "UTC")
    assert out == "16/06/2026 09:30"


def test_format_datetime_en_us_12h() -> None:
    dt = datetime(2026, 6, 16, 9, 30, tzinfo=timezone.utc)
    out = format_datetime(dt, Locale.EN_US, "UTC")
    assert out == "06/16/2026, 9:30 AM"


def test_format_datetime_timezone_conversion() -> None:
    dt = datetime(2026, 6, 16, 9, 30, tzinfo=timezone.utc)
    out = format_datetime(dt, Locale.EN_US, "Asia/Ho_Chi_Minh")
    # UTC+7
    assert out.endswith("PM")
    assert "16" in out


def test_format_datetime_naive_assumed_utc() -> None:
    dt = datetime(2026, 6, 16, 9, 30)
    out = format_datetime(dt, Locale.EN_US, "UTC")
    assert out == "06/16/2026, 9:30 AM"


def test_format_date_vi_vn() -> None:
    dt = datetime(2026, 6, 16, 9, 30, tzinfo=timezone.utc)
    assert format_date(dt, Locale.VI_VN, "UTC") == "16/06/2026"


def test_format_date_en_us() -> None:
    dt = datetime(2026, 6, 16, 9, 30, tzinfo=timezone.utc)
    assert format_date(dt, Locale.EN_US, "UTC") == "06/16/2026"


def test_format_time_vi_vn() -> None:
    dt = datetime(2026, 6, 16, 9, 30, tzinfo=timezone.utc)
    assert format_time(dt, Locale.VI_VN, "UTC") == "09:30"


def test_format_time_en_us() -> None:
    dt = datetime(2026, 6, 16, 9, 30, tzinfo=timezone.utc)
    assert format_time(dt, Locale.EN_US, "UTC") == "9:30 AM"


def test_format_datetime_empty() -> None:
    assert format_datetime(None, Locale.EN_US, "UTC") == ""


# ---------------------------------------------------------------------------
# Unicode normalization
# ---------------------------------------------------------------------------


def test_normalize_search_vi_vn_nfc() -> None:
    # NFD: "ấ" as a + combining circumflex + combining acute
    nfd = "a\u0302\u0301p"
    out = normalize_search(nfd, Locale.VI_VN)
    # NFC: "ấ" as a single precomposed codepoint
    nfc = "\u1ea5p"
    assert out == nfc


def test_normalize_search_en_us_nfc() -> None:
    out = normalize_search("Hello", Locale.EN_US)
    assert out == "Hello"


def test_normalize_search_empty() -> None:
    assert normalize_search("", Locale.VI_VN) == ""
    assert normalize_search(None, Locale.VI_VN) == ""


# ---------------------------------------------------------------------------
# Service parsers wrap domain errors
# ---------------------------------------------------------------------------


def test_service_parse_locale_unsupported_raises_service_error() -> None:
    svc = I18nService.__new__(I18nService)
    with pytest.raises(I18nUnsupportedLocale) as exc:
        svc.parse_locale("fr-FR")
    assert exc.value.rejection_code == "LOCALE_UNSUPPORTED"


def test_service_parse_timezone_invalid_raises_service_error() -> None:
    svc = I18nService.__new__(I18nService)
    with pytest.raises(I18nInvalidTimezone) as exc:
        svc.parse_timezone("Not/AZone")
    assert exc.value.rejection_code == "TIMEZONE_INVALID"


# ---------------------------------------------------------------------------
# View dataclasses
# ---------------------------------------------------------------------------


def test_user_locale_view_dataclass() -> None:
    view = UserLocaleView(
        user_id="00000000-0000-0000-0000-000000000001",
        organization_id="00000000-0000-0000-0000-000000000002",
        locale="vi-VN",
        timezone="Asia/Ho_Chi_Minh",
        resolved_locale="vi-VN",
        resolved_timezone="Asia/Ho_Chi_Minh",
        locale_source="user",
        timezone_source="user",
    )
    assert view.locale == "vi-VN"
    assert view.locale_source == "user"


def test_organization_locale_view_dataclass() -> None:
    view = OrganizationLocaleView(
        organization_id="00000000-0000-0000-0000-000000000002",
        default_locale="en-US",
        default_timezone="UTC",
    )
    assert view.default_locale == "en-US"
    assert view.default_timezone == "UTC"
