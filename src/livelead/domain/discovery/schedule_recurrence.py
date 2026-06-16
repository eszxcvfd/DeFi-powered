"""Bounded recurrence validation and next-run calculation (US-035)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo


class RecurrenceKind(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    CRON = "cron"


_CRON_RE = re.compile(
    r"^(\d{1,2}|\*)\s+(\d{1,2}|\*)\s+(\*)\s+(\*)\s+(\*|\d)$"
)


@dataclass(frozen=True)
class RecurrenceSpec:
    kind: RecurrenceKind
    timezone: str
    hour: int = 9
    minute: int = 0
    day_of_week: int = 0  # Monday=0 .. Sunday=6
    cron_expression: str | None = None

    def summary(self) -> str:
        if self.kind == RecurrenceKind.DAILY:
            return f"Daily at {self.hour:02d}:{self.minute:02d} ({self.timezone})"
        if self.kind == RecurrenceKind.WEEKLY:
            days = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
            return f"Weekly on {days[self.day_of_week]} {self.hour:02d}:{self.minute:02d} ({self.timezone})"
        return f"Cron {self.cron_expression} ({self.timezone})"


def validate_timezone(tz_name: str) -> None:
    try:
        ZoneInfo(tz_name)
    except Exception as exc:
        raise ValueError(f"invalid timezone: {tz_name}") from exc


def parse_recurrence(payload: dict) -> RecurrenceSpec:
    kind_raw = str(payload.get("kind", "")).lower()
    tz = str(payload.get("timezone", "UTC")).strip() or "UTC"
    validate_timezone(tz)

    if kind_raw == RecurrenceKind.DAILY:
        hour = int(payload.get("hour", 9))
        minute = int(payload.get("minute", 0))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("hour/minute out of range")
        return RecurrenceSpec(kind=RecurrenceKind.DAILY, timezone=tz, hour=hour, minute=minute)

    if kind_raw == RecurrenceKind.WEEKLY:
        hour = int(payload.get("hour", 9))
        minute = int(payload.get("minute", 0))
        dow = int(payload.get("day_of_week", 0))
        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= dow <= 6):
            raise ValueError("weekly fields out of range")
        return RecurrenceSpec(
            kind=RecurrenceKind.WEEKLY,
            timezone=tz,
            hour=hour,
            minute=minute,
            day_of_week=dow,
        )

    if kind_raw == RecurrenceKind.CRON:
        expr = str(payload.get("cron_expression", "")).strip()
        if not _CRON_RE.match(expr):
            raise ValueError(
                "cron must be restricted form: minute hour * * * (minute/hour fixed, dom/month *)"
            )
        parts = expr.split()
        minute_s, hour_s = parts[0], parts[1]
        if minute_s == "*" or hour_s == "*":
            raise ValueError("cron minute and hour must be fixed integers for bounded recurrence")
        minute = int(minute_s)
        hour = int(hour_s)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("cron hour/minute out of range")
        return RecurrenceSpec(
            kind=RecurrenceKind.CRON,
            timezone=tz,
            hour=hour,
            minute=minute,
            cron_expression=expr,
        )

    raise ValueError("kind must be daily, weekly, or cron")


def recurrence_to_json(spec: RecurrenceSpec) -> dict:
    base: dict = {"kind": spec.kind.value, "timezone": spec.timezone}
    if spec.kind == RecurrenceKind.DAILY:
        base.update({"hour": spec.hour, "minute": spec.minute})
    elif spec.kind == RecurrenceKind.WEEKLY:
        base.update({"hour": spec.hour, "minute": spec.minute, "day_of_week": spec.day_of_week})
    else:
        base["cron_expression"] = spec.cron_expression
    return base


def _local_now(tz_name: str, after: datetime | None) -> datetime:
    tz = ZoneInfo(tz_name)
    if after is None:
        return datetime.now(tz)
    if after.tzinfo is None:
        after = after.replace(tzinfo=UTC)
    return after.astimezone(tz)


def compute_next_run(spec: RecurrenceSpec, after: datetime | None = None) -> datetime:
    """Return next run instant in UTC."""
    local = _local_now(spec.timezone, after)
    if after is not None:
        local = local + timedelta(seconds=1)

    if spec.kind in (RecurrenceKind.DAILY, RecurrenceKind.CRON):
        candidate = local.replace(hour=spec.hour, minute=spec.minute, second=0, microsecond=0)
        if candidate <= local:
            candidate = candidate + timedelta(days=1)
        return candidate.astimezone(UTC)

    # weekly
    target_dow = spec.day_of_week
    days_ahead = (target_dow - local.weekday()) % 7
    candidate = local.replace(hour=spec.hour, minute=spec.minute, second=0, microsecond=0) + timedelta(
        days=days_ahead
    )
    if candidate <= local:
        candidate = candidate + timedelta(days=7)
    return candidate.astimezone(UTC)