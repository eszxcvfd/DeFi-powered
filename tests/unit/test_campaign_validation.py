from livelead.domain.campaigns.validation import validate_campaign_name, validate_scoring_weights


def test_validate_campaign_name():
    assert validate_campaign_name("  ") == ["name is required"]
    assert validate_campaign_name("OK") == []


def test_validate_scoring_weights_unknown_key():
    weights, errors = validate_scoring_weights({"topic_relevance": 1.0, "bogus": 0.1})
    assert weights is None
    assert any("unknown" in e for e in errors)


def test_validate_scoring_weights_normalizes():
    weights, errors = validate_scoring_weights({"topic_relevance": 0.5, "icp_match": 0.5})
    assert not errors
    assert weights is not None
    assert abs(sum(weights.weights.values()) - 1.0) < 0.01