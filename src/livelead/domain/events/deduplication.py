"""Deterministic deduplication heuristics — explainable merges."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class MergeReason(StrEnum):
    SAME_SOURCE_URL = "same_source_url"
    SAME_CANONICAL_FINGERPRINT = "same_canonical_fingerprint"
    NEW_EVENT = "new_event"


@dataclass(frozen=True, slots=True)
class MergeDecision:
    should_merge: bool
    reason: MergeReason
    explanation: str


def normalize_title(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def canonical_fingerprint(title: str, region: str = "") -> str:
    return f"{normalize_title(title)}|{region.lower().strip()}"


def external_id_from_url(source_url: str) -> str:
    return source_url.rstrip("/").rsplit("/", 1)[-1].lower()


def decide_merge(
    *,
    finding_title: str,
    finding_region: str,
    finding_source_url: str,
    existing_canonical_title: str,
    existing_region: str,
    existing_source_url: str,
) -> MergeDecision:
    if finding_source_url.strip().lower() == existing_source_url.strip().lower():
        return MergeDecision(
            should_merge=True,
            reason=MergeReason.SAME_SOURCE_URL,
            explanation="Finding matches an existing event source URL in this campaign.",
        )
    fp_new = canonical_fingerprint(finding_title, finding_region)
    fp_old = canonical_fingerprint(existing_canonical_title, existing_region)
    if fp_new and fp_new == fp_old:
        return MergeDecision(
            should_merge=True,
            reason=MergeReason.SAME_CANONICAL_FINGERPRINT,
            explanation=(
                "Normalized title and region match an existing canonical event; "
                "linking a new source observation."
            ),
        )
    ext_new = external_id_from_url(finding_source_url)
    ext_old = external_id_from_url(existing_source_url)
    if ext_new and ext_new == ext_old and len(ext_new) > 3:
        return MergeDecision(
            should_merge=True,
            reason=MergeReason.SAME_CANONICAL_FINGERPRINT,
            explanation="External id derived from source URL matches an existing event.",
        )
    return MergeDecision(
        should_merge=False,
        reason=MergeReason.NEW_EVENT,
        explanation="No deduplication rule matched; creating a new canonical event.",
    )
