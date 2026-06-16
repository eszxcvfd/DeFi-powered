"""Pure rules for query expansion approval and snapshots (US-036)."""

from __future__ import annotations

from livelead.domain.query_expansion.models import (
    QueryExpansionGenerationMode,
    QueryExpansionSetStatus,
    QueryExpansionVariant,
    QueryVariantSource,
)


def active_variants(variants: list[QueryExpansionVariant]) -> list[QueryExpansionVariant]:
    return [v for v in variants if not v.removed and v.text.strip()]


def set_requires_review(
    variants: list[QueryExpansionVariant],
    generation_mode: QueryExpansionGenerationMode,
) -> bool:
    if generation_mode == QueryExpansionGenerationMode.AI_ASSISTED:
        return any(v.source == QueryVariantSource.AI for v in active_variants(variants))
    return False


def derive_status_after_save(
    *,
    approve: bool,
    variants: list[QueryExpansionVariant],
    generation_mode: QueryExpansionGenerationMode,
) -> QueryExpansionSetStatus:
    active = active_variants(variants)
    if approve:
        if not active:
            return QueryExpansionSetStatus.APPROVED
        if set_requires_review(variants, generation_mode):
            return QueryExpansionSetStatus.APPROVED
        return QueryExpansionSetStatus.APPROVED
    if set_requires_review(variants, generation_mode):
        return QueryExpansionSetStatus.PENDING_REVIEW
    return QueryExpansionSetStatus.DRAFT


def may_use_for_discovery_run(status: QueryExpansionSetStatus) -> bool:
    return status == QueryExpansionSetStatus.APPROVED


def merge_expanded_keywords(
    base_positive: list[str],
    variants: list[QueryExpansionVariant],
) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for term in base_positive:
        key = term.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(term.strip())
    for v in active_variants(variants):
        key = v.text.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(v.text.strip())
    return out


def variant_to_dict(v: QueryExpansionVariant) -> dict:
    return {
        "text": v.text,
        "variant_type": v.variant_type.value,
        "source": v.source.value,
        "confidence": v.confidence,
        "assumption": v.assumption,
        "user_edited": v.user_edited,
        "removed": v.removed,
    }