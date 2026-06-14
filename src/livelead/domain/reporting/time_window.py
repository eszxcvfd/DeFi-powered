"""Normalize dashboard date-range selection (US-014)."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta


class InvalidDashboardTimeWindow(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class NormalizedTimeWindow:
    start: date
    end: date
    preset: str | None


def _utc_today() -> date:
    return datetime.now(UTC).date()


def normalize_time_window(
    *,
    start: date | None = None,
    end: date | None = None,
    preset: str | None = None,
    today: date | None = None,
) -> NormalizedTimeWindow:
    ref = today or _utc_today()
    if preset:
        key = preset.strip().lower()
        if key == "last_7_days":
            end_d = ref
            start_d = ref - timedelta(days=6)
            return NormalizedTimeWindow(start=start_d, end=end_d, preset=key)
        if key == "last_30_days":
            end_d = ref
            start_d = ref - timedelta(days=29)
            return NormalizedTimeWindow(start=start_d, end=end_d, preset=key)
        if key == "this_month":
            start_d = ref.replace(day=1)
            return NormalizedTimeWindow(start=start_d, end=ref, preset=key)
        raise InvalidDashboardTimeWindow(f"unsupported preset: {preset}")

    if start is None and end is None:
        end_d = ref
        start_d = ref - timedelta(days=29)
        return NormalizedTimeWindow(start=start_d, end=end_d, preset="last_30_days")

    if start is None or end is None:
        raise InvalidDashboardTimeWindow("start and end are required when preset is omitted")

    if end < start:
        raise InvalidDashboardTimeWindow("end must be on or after start")

    span = (end - start).days
    if span > 366:
        raise InvalidDashboardTimeWindow("time window must not exceed 366 days")

    return NormalizedTimeWindow(start=start, end=end, preset=None)


def window_bounds_utc(window: NormalizedTimeWindow) -> tuple[datetime, datetime]:
    """Inclusive calendar dates mapped to UTC datetime bounds for queries."""
    start_dt = datetime(window.start.year, window.start.month, window.start.day, tzinfo=UTC)
    end_exclusive = datetime(
        window.end.year, window.end.month, window.end.day, tzinfo=UTC
    ) + timedelta(days=1)
    return start_dt, end_exclusive
