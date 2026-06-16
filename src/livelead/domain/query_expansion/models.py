"""Governed query expansion domain model (US-036)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class QueryVariantType(StrEnum):
    SYNONYM = "synonym"
    ABBREVIATION = "abbreviation"
    LANGUAGE = "language"
    INDUSTRY_PHRASE = "industry_phrase"
    USER = "user"


class QueryVariantSource(StrEnum):
    USER = "user"
    RULE = "rule"
    AI = "ai"


class QueryExpansionSetStatus(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


class QueryExpansionGenerationMode(StrEnum):
    RULE = "rule"
    AI_ASSISTED = "ai_assisted"


@dataclass(frozen=True)
class QueryExpansionVariant:
    text: str
    variant_type: QueryVariantType
    source: QueryVariantSource
    confidence: float | None = None
    assumption: str | None = None
    user_edited: bool = False
    removed: bool = False


@dataclass
class QueryExpansionSet:
    id: str
    campaign_id: str
    organization_id: str
    status: QueryExpansionSetStatus
    generation_mode: QueryExpansionGenerationMode
    variants: list[QueryExpansionVariant] = field(default_factory=list)
    version: int = 1


@dataclass(frozen=True)
class QueryExpansionSnapshot:
    """Immutable payload stored on discovery jobs."""

    expansion_set_id: str
    expansion_set_version: int
    generation_mode: str
    variants: tuple[dict, ...]
    expanded_positive_keywords: tuple[str, ...]