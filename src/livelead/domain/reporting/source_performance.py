"""Source-performance grouped reporting (US-017)."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class InvalidSourceGrouping(ValueError):
    pass


class SourceGrouping(StrEnum):
    PLATFORM = "platform"
    CONNECTOR = "connector"
    CAMPAIGN = "campaign"
    INDUSTRY = "industry"


GROUPING_LABELS: dict[SourceGrouping, str] = {
    SourceGrouping.PLATFORM: "Platform (connector type)",
    SourceGrouping.CONNECTOR: "Connector (source)",
    SourceGrouping.CAMPAIGN: "Campaign",
    SourceGrouping.INDUSTRY: "Industry",
}


def normalize_grouping(raw: str | None) -> SourceGrouping:
    if not raw or not raw.strip():
        return SourceGrouping.CAMPAIGN
    key = raw.strip().lower()
    try:
        return SourceGrouping(key)
    except ValueError as exc:
        raise InvalidSourceGrouping(f"unsupported grouping: {raw}") from exc


@dataclass(frozen=True, slots=True)
class SourcePerformanceMetrics:
    events_discovered: int = 0
    events_prioritized: int = 0
    leads_created: int = 0
    opportunities: int = 0


@dataclass(frozen=True, slots=True)
class SourcePerformanceRow:
    group_key: str
    group_label: str
    metrics: SourcePerformanceMetrics


@dataclass(frozen=True, slots=True)
class UnattributedSourceSummary:
    events_without_source_link: int = 0
    leads_without_group_key: int = 0
    explanation: str = ""


@dataclass(frozen=True, slots=True)
class SourcePerformanceFreshness:
    last_updated_at: datetime | None
    source: str


@dataclass(frozen=True, slots=True)
class SourcePerformanceWindow:
    start: date
    end: date
    preset: str | None


@dataclass(frozen=True, slots=True)
class SourcePerformanceReport:
    grouping: SourceGrouping
    grouping_label: str
    window: SourcePerformanceWindow
    rows: tuple[SourcePerformanceRow, ...]
    unattributed: UnattributedSourceSummary | None
    freshness: SourcePerformanceFreshness
    generated_at: datetime


def build_unattributed_explanation(grouping: SourceGrouping) -> str:
    if grouping in (SourceGrouping.PLATFORM, SourceGrouping.CONNECTOR):
        return (
            "Events without a source observation and leads without an event-linked source "
            "are excluded from grouped rows and counted here."
        )
    if grouping == SourceGrouping.CAMPAIGN:
        return "Leads and events without a campaign assignment are excluded from grouped rows."
    return "Records without a campaign industry (target industry) are excluded from grouped rows."


def sort_rows(rows: list[SourcePerformanceRow]) -> tuple[SourcePerformanceRow, ...]:
    return tuple(sorted(rows, key=lambda r: (-r.metrics.events_discovered, r.group_label.lower())))
