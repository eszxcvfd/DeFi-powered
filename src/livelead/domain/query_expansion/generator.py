"""Deterministic query expansion generation (US-036)."""

from __future__ import annotations

from livelead.domain.query_expansion.models import (
    QueryExpansionGenerationMode,
    QueryExpansionVariant,
    QueryVariantSource,
    QueryVariantType,
)

_SYNONYM_MAP: dict[str, list[str]] = {
    "summit": ["conference", "forum"],
    "conference": ["summit", "symposium"],
    "meetup": ["gathering", "networking event"],
    "webinar": ["online seminar", "virtual session"],
    "expo": ["trade show", "exhibition"],
    "hackathon": ["buildathon", "coding sprint"],
}

_ABBREV_HINTS: dict[str, str] = {
    "artificial intelligence": "AI",
    "machine learning": "ML",
    "chief technology officer": "CTO",
    "software as a service": "SaaS",
}


def _industry_phrases(industry: str, keywords: list[str]) -> list[QueryExpansionVariant]:
    industry = (industry or "").strip()
    if not industry:
        return []
    out: list[QueryExpansionVariant] = []
    for kw in keywords[:5]:
        phrase = f"{industry} {kw}".strip()
        if phrase:
            out.append(
                QueryExpansionVariant(
                    text=phrase,
                    variant_type=QueryVariantType.INDUSTRY_PHRASE,
                    source=QueryVariantSource.RULE,
                    confidence=0.7,
                    assumption="Combines campaign industry with base keyword",
                )
            )
    return out


def _synonyms(keywords: list[str]) -> list[QueryExpansionVariant]:
    out: list[QueryExpansionVariant] = []
    for kw in keywords:
        key = kw.strip().lower()
        for alt in _SYNONYM_MAP.get(key, []):
            out.append(
                QueryExpansionVariant(
                    text=alt,
                    variant_type=QueryVariantType.SYNONYM,
                    source=QueryVariantSource.RULE,
                    confidence=0.85,
                )
            )
    return out


def _abbreviations(keywords: list[str], description: str) -> list[QueryExpansionVariant]:
    corpus = " ".join(keywords) + " " + (description or "")
    lower = corpus.lower()
    out: list[QueryExpansionVariant] = []
    for phrase, abbr in _ABBREV_HINTS.items():
        if phrase in lower or any(phrase in k.lower() for k in keywords):
            out.append(
                QueryExpansionVariant(
                    text=abbr,
                    variant_type=QueryVariantType.ABBREVIATION,
                    source=QueryVariantSource.RULE,
                    confidence=0.8,
                    assumption=f"Abbreviation inferred for '{phrase}'",
                )
            )
    for kw in keywords:
        parts = kw.split()
        if len(parts) >= 2:
            abbr = "".join(p[0].upper() for p in parts if p)
            if len(abbr) >= 2:
                out.append(
                    QueryExpansionVariant(
                        text=abbr,
                        variant_type=QueryVariantType.ABBREVIATION,
                        source=QueryVariantSource.AI,
                        confidence=0.55,
                        assumption="Initialism suggested from multi-word keyword",
                    )
                )
    return out


def _language_variants(keywords: list[str]) -> list[QueryExpansionVariant]:
    """Bounded alternate phrasing placeholders (not full translation admin)."""
    out: list[QueryExpansionVariant] = []
    for kw in keywords:
        if "event" in kw.lower():
            out.append(
                QueryExpansionVariant(
                    text=kw.replace("event", "sự kiện"),
                    variant_type=QueryVariantType.LANGUAGE,
                    source=QueryVariantSource.AI,
                    confidence=0.5,
                    assumption="Alternate language phrasing; review before use",
                )
            )
    return out


def generate_candidate_variants(
    *,
    positive_keywords: list[str],
    target_industry: str,
    description: str,
    mode: QueryExpansionGenerationMode = QueryExpansionGenerationMode.AI_ASSISTED,
) -> tuple[list[QueryExpansionVariant], QueryExpansionGenerationMode]:
    keywords = [k.strip() for k in positive_keywords if k and str(k).strip()]
    if not keywords:
        return [], QueryExpansionGenerationMode.RULE

    variants: list[QueryExpansionVariant] = []
    variants.extend(_synonyms(keywords))
    variants.extend(_abbreviations(keywords, description))
    variants.extend(_language_variants(keywords))
    variants.extend(_industry_phrases(target_industry, keywords))

    # Deduplicate by text (case-insensitive), preserve first
    seen: set[str] = set()
    deduped: list[QueryExpansionVariant] = []
    base_lower = {k.lower() for k in keywords}
    for v in variants:
        key = v.text.strip().lower()
        if not key or key in base_lower or key in seen:
            continue
        seen.add(key)
        deduped.append(v)

    resolved_mode = mode
    if any(v.source == QueryVariantSource.AI for v in deduped):
        resolved_mode = QueryExpansionGenerationMode.AI_ASSISTED
    else:
        resolved_mode = QueryExpansionGenerationMode.RULE
    return deduped[:40], resolved_mode