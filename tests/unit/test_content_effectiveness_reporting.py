"""US-018 content-effectiveness domain rules."""

import pytest

from livelead.domain.reporting.content_effectiveness import (
    CORRELATION_DISCLAIMER,
    ContentEffectivenessMetrics,
    ContentEffectivenessRow,
    ContentGrouping,
    InvalidContentGrouping,
    build_unattributed_explanation,
    normalize_content_grouping,
    sort_content_rows,
)


def test_normalize_content_grouping_defaults():
    assert normalize_content_grouping(None) == ContentGrouping.CONTENT_TYPE


def test_normalize_content_grouping_keys():
    for key in ("content_type", "tone", "template"):
        assert normalize_content_grouping(key) == ContentGrouping(key)


def test_invalid_content_grouping():
    with pytest.raises(InvalidContentGrouping):
        normalize_content_grouping("platform")


def test_correlation_note_present():
    assert "correlation" in CORRELATION_DISCLAIMER.lower()


def test_sort_content_rows():
    rows = sort_content_rows(
        [
            ContentEffectivenessRow("b", "B", ContentEffectivenessMetrics(content_used=1)),
            ContentEffectivenessRow("a", "A", ContentEffectivenessMetrics(content_used=3)),
        ]
    )
    assert rows[0].group_key == "a"


def test_unattributed_explanation_mentions_metadata():
    assert "metadata" in build_unattributed_explanation(ContentGrouping.TONE).lower()
