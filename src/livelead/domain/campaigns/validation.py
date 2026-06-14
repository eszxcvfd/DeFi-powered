"""Pure validation for campaign payloads."""

from livelead.domain.campaigns.models import DEFAULT_SCORING_WEIGHTS, ScoringWeights

ALLOWED_WEIGHT_KEYS = frozenset(DEFAULT_SCORING_WEIGHTS.keys())
MIN_NAME_LEN = 1
MAX_NAME_LEN = 200


def validate_campaign_name(name: str) -> list[str]:
    errors: list[str] = []
    trimmed = name.strip()
    if len(trimmed) < MIN_NAME_LEN:
        errors.append("name is required")
    elif len(trimmed) > MAX_NAME_LEN:
        errors.append(f"name must be at most {MAX_NAME_LEN} characters")
    return errors


def validate_scoring_weights(raw: dict[str, float]) -> tuple[ScoringWeights | None, list[str]]:
    errors: list[str] = []
    if not raw:
        return ScoringWeights(), errors
    unknown = set(raw) - ALLOWED_WEIGHT_KEYS
    if unknown:
        errors.append(f"unknown scoring weight keys: {sorted(unknown)}")
    if errors:
        return None, errors
    cleaned: dict[str, float] = {}
    for key in ALLOWED_WEIGHT_KEYS:
        value = raw.get(key, DEFAULT_SCORING_WEIGHTS[key])
        if value < 0:
            errors.append(f"{key} must be non-negative")
        cleaned[key] = float(value)
    if errors:
        return None, errors
    weights = ScoringWeights(weights=cleaned).normalized()
    total = sum(weights.weights.values())
    if abs(total - 1.0) > 0.001 and sum(cleaned.values()) > 0:
        pass  # normalized handles
    return weights, errors