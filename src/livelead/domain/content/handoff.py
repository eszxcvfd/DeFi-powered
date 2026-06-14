"""Approved-content handoff and usage lifecycle (US-011)."""

from enum import StrEnum

from livelead.domain.content.models import ContentReviewStatus, ContentUsageStatus

SUPPORTED_EXPORT_FORMATS = frozenset({"markdown", "csv"})


class HandoffAction(StrEnum):
    COPY = "copy"
    EXPORT = "export"
    MARK_USED = "mark_used"


def may_handoff_content(review_status: ContentReviewStatus) -> bool:
    return review_status == ContentReviewStatus.APPROVED


def can_mark_used(usage_status: ContentUsageStatus) -> bool:
    return usage_status == ContentUsageStatus.NOT_USED


def normalize_export_format(raw: str) -> str | None:
    key = (raw or "").strip().lower()
    if key in SUPPORTED_EXPORT_FORMATS:
        return key
    return None