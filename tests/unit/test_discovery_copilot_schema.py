"""US-037 discovery copilot schema and grounding."""

import pytest

from livelead.domain.discovery_copilot.grounding import question_within_discovery_scope
from livelead.domain.discovery_copilot.schema import CopilotSchemaError, validate_structured_response


def test_validate_requires_claims():
    with pytest.raises(CopilotSchemaError):
        validate_structured_response({"claims": [], "confidence": 0.5})


def test_validate_full_payload():
    resp = validate_structured_response(
        {
            "claims": [{"text": "Focus on summit keywords"}],
            "evidence": [{"summary": "Campaign keywords", "source_ref": "campaign"}],
            "confidence": 0.6,
            "assumptions": ["Bounded to campaign"],
            "risk_flags": [{"code": "low_confidence", "message": "Review"}],
            "proposed_query_framing": ["tech summit"],
            "recommended_source_ids": [],
        }
    )
    assert resp.confidence == 0.6
    assert resp.claims[0].text.startswith("Focus")


def test_question_scope_rejects_outreach():
    ok, reason = question_within_discovery_scope("Please draft a cold email for this list")
    assert not ok
    assert reason


def test_question_scope_accepts_discovery():
    ok, _ = question_within_discovery_scope(
        "Which livestream discovery keywords should we widen for this campaign?"
    )
    assert ok