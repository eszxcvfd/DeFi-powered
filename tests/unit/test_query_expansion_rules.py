"""US-036 query expansion domain rules."""

from livelead.domain.query_expansion.generator import generate_candidate_variants
from livelead.domain.query_expansion.models import (
    QueryExpansionGenerationMode,
    QueryExpansionSetStatus,
    QueryExpansionVariant,
    QueryVariantSource,
    QueryVariantType,
)
from livelead.domain.query_expansion.rules import (
    may_use_for_discovery_run,
    merge_expanded_keywords,
    set_requires_review,
)


def test_ai_variants_require_review():
    variants = [
        QueryExpansionVariant(
            text="AI",
            variant_type=QueryVariantType.ABBREVIATION,
            source=QueryVariantSource.AI,
        )
    ]
    assert set_requires_review(variants, QueryExpansionGenerationMode.AI_ASSISTED)


def test_approved_only_for_discovery():
    assert may_use_for_discovery_run(QueryExpansionSetStatus.APPROVED)
    assert not may_use_for_discovery_run(QueryExpansionSetStatus.PENDING_REVIEW)


def test_merge_expanded_keywords_dedupes():
    base = ["Summit"]
    variants = [
        QueryExpansionVariant("conference", QueryVariantType.SYNONYM, QueryVariantSource.RULE),
        QueryExpansionVariant("summit", QueryVariantType.SYNONYM, QueryVariantSource.RULE),
    ]
    merged = merge_expanded_keywords(base, variants)
    assert "Summit" in merged
    assert "conference" in merged
    assert len(merged) == 2


def test_generate_from_summit_keyword():
    variants, mode = generate_candidate_variants(
        positive_keywords=["summit"],
        target_industry="Tech",
        description="",
    )
    texts = {v.text for v in variants}
    assert "conference" in texts or "forum" in texts
    assert mode in (
        QueryExpansionGenerationMode.AI_ASSISTED,
        QueryExpansionGenerationMode.RULE,
    )