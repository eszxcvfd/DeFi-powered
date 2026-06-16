"""US-037 copilot payload normalization."""

from livelead.domain.discovery_copilot.normalize import normalize_provider_payload
from livelead.domain.discovery_copilot.schema import validate_structured_response


def test_empty_claims_get_fallback():
    raw = normalize_provider_payload(
        {"proposed_query_framing": ["tech summit"], "confidence": 0.6},
        campaign_name="Camp A",
        question="What keywords for livestreams?",
    )
    structured = validate_structured_response(raw)
    assert len(structured.claims) >= 1
    assert structured.proposed_query_framing


def test_string_claims_coerced():
    raw = normalize_provider_payload(
        {"claims": ["Focus on DeFi events"], "confidence": 0.7},
        campaign_name="X",
        question="q",
    )
    structured = validate_structured_response(raw)
    assert structured.claims[0].text == "Focus on DeFi events"