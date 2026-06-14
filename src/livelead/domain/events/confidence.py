"""Confidence metadata for canonical vs inferred fields."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FieldTrust(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    MERGED = "merged"


@dataclass(frozen=True, slots=True)
class FieldConfidence:
    field: str
    trust: FieldTrust
    note: str = ""


def confidence_for_new_event(*, has_organizer: bool, has_region: bool, has_starts_at: bool) -> list[FieldConfidence]:
    fields: list[FieldConfidence] = [
        FieldConfidence("canonical_title", FieldTrust.OBSERVED, "From source observation title"),
        FieldConfidence("source_url", FieldTrust.OBSERVED, "From source observation URL"),
        FieldConfidence("description", FieldTrust.OBSERVED, "From source payload"),
    ]
    if has_organizer:
        fields.append(FieldConfidence("organizer", FieldTrust.OBSERVED, "From source payload"))
    else:
        fields.append(FieldConfidence("organizer", FieldTrust.INFERRED, "Not provided by source"))
    if has_region:
        fields.append(FieldConfidence("region", FieldTrust.OBSERVED, "From source payload"))
    else:
        fields.append(FieldConfidence("region", FieldTrust.INFERRED, "Not provided by source"))
    if has_starts_at:
        fields.append(FieldConfidence("starts_at", FieldTrust.INFERRED, "Derived scheduling placeholder"))
    else:
        fields.append(FieldConfidence("starts_at", FieldTrust.INFERRED, "Missing start time"))
    return fields


def confidence_after_merge() -> list[FieldConfidence]:
    return [
        FieldConfidence("canonical_title", FieldTrust.MERGED, "Retained from first canonical record"),
        FieldConfidence("description", FieldTrust.MERGED, "May combine multiple source observations"),
        FieldConfidence("organizer", FieldTrust.MERGED, "May differ across sources; canonical value retained"),
        FieldConfidence("region", FieldTrust.MERGED, "May differ across sources; canonical value retained"),
    ]


def summary_confidence(fields: list[FieldConfidence]) -> str:
    trusts = {f.trust for f in fields}
    if FieldTrust.OBSERVED in trusts and FieldTrust.INFERRED not in trusts and FieldTrust.MERGED not in trusts:
        return "high"
    if FieldTrust.MERGED in trusts:
        return "merged"
    if FieldTrust.INFERRED in trusts:
        return "medium"
    return "medium"