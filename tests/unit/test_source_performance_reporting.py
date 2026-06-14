"""US-017 source-performance domain rules."""

import pytest

from livelead.domain.reporting.source_performance import (
    InvalidSourceGrouping,
    SourceGrouping,
    SourcePerformanceMetrics,
    SourcePerformanceRow,
    build_unattributed_explanation,
    normalize_grouping,
    sort_rows,
)


def test_normalize_grouping_defaults_to_campaign():
    assert normalize_grouping(None) == SourceGrouping.CAMPAIGN
    assert normalize_grouping("  campaign  ") == SourceGrouping.CAMPAIGN


def test_normalize_grouping_all_keys():
    for key in ("platform", "connector", "campaign", "industry"):
        assert normalize_grouping(key) == SourceGrouping(key)


def test_invalid_grouping_raises():
    with pytest.raises(InvalidSourceGrouping, match="unsupported"):
        normalize_grouping("domain")


def test_build_unattributed_explanation_varies_by_grouping():
    assert "source observation" in build_unattributed_explanation(SourceGrouping.PLATFORM).lower()
    assert "campaign" in build_unattributed_explanation(SourceGrouping.CAMPAIGN).lower()
    assert "industry" in build_unattributed_explanation(SourceGrouping.INDUSTRY).lower()


def test_sort_rows_by_discovered_then_label():
    rows = sort_rows(
        [
            SourcePerformanceRow("b", "Beta", SourcePerformanceMetrics(events_discovered=1)),
            SourcePerformanceRow("a", "Alpha", SourcePerformanceMetrics(events_discovered=5)),
            SourcePerformanceRow("c", "Gamma", SourcePerformanceMetrics(events_discovered=5)),
        ]
    )
    assert [r.group_key for r in rows] == ["a", "c", "b"]
