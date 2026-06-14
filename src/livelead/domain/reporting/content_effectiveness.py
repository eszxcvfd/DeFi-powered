"""Content-effectiveness grouped reporting (US-018)."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

CORRELATION_DISCLAIMER = "Grouped metrics show correlation between used content metadata and recorded outcomes, not causation."


class InvalidContentGrouping(ValueError):
    pass


class ContentGrouping(StrEnum):
    CONTENT_TYPE = "content_type"
    TONE = "tone"
    TEMPLATE = "template"


GROUPING_LABELS: dict[ContentGrouping, str] = {
    ContentGrouping.CONTENT_TYPE: "Content type",
    ContentGrouping.TONE: "Tone",
    ContentGrouping.TEMPLATE: "Template version",
}


def normalize_content_grouping(raw: str | None) -> ContentGrouping:
    if not raw or not raw.strip():
        return ContentGrouping.CONTENT_TYPE
    key = raw.strip().lower()
    try:
        return ContentGrouping(key)
    except ValueError as exc:
        raise InvalidContentGrouping(f"unsupported grouping: {raw}") from exc


@dataclass(frozen=True, slots=True)
class ContentEffectivenessMetrics:
    content_used: int = 0
    outcomes_linked: int = 0
    outcomes_contact: int = 0
    outcomes_response: int = 0
    outcomes_meeting: int = 0
    outcomes_opportunity: int = 0


@dataclass(frozen=True, slots=True)
class ContentEffectivenessRow:
    group_key: str
    group_label: str
    metrics: ContentEffectivenessMetrics


@dataclass(frozen=True, slots=True)
class UnattributedContentSummary:
    used_content_without_metadata: int = 0
    outcomes_without_content_link: int = 0
    explanation: str = ""


@dataclass(frozen=True, slots=True)
class ContentEffectivenessFreshness:
    last_updated_at: datetime | None
    source: str


@dataclass(frozen=True, slots=True)
class ContentEffectivenessWindow:
    start: date
    end: date
    preset: str | None


@dataclass(frozen=True, slots=True)
class ContentEffectivenessReport:
    grouping: ContentGrouping
    grouping_label: str
    window: ContentEffectivenessWindow
    rows: tuple[ContentEffectivenessRow, ...]
    unattributed: UnattributedContentSummary | None
    freshness: ContentEffectivenessFreshness
    correlation_note: str
    generated_at: datetime


def build_unattributed_explanation(grouping: ContentGrouping) -> str:
    if grouping == ContentGrouping.TEMPLATE:
        return (
            "Used content missing template version metadata and outcomes without an explicit "
            "content link are excluded from grouped rows."
        )
    return (
        f"Used content missing {GROUPING_LABELS[grouping].lower()} metadata and outcomes "
        "without a linked used draft are excluded from grouped rows."
    )


def sort_content_rows(rows: list[ContentEffectivenessRow]) -> tuple[ContentEffectivenessRow, ...]:
    return tuple(sorted(rows, key=lambda r: (-r.metrics.content_used, r.group_label.lower())))
