from datetime import date

from livelead.domain.reporting.funnel import FUNNEL_COHORT_RULE, build_funnel_steps
from livelead.domain.reporting.time_window import normalize_time_window


def test_funnel_cohort_rule_documented():
    assert "observed_at" in FUNNEL_COHORT_RULE
    assert "outcome" in FUNNEL_COHORT_RULE.lower()


def test_build_funnel_steps_manual_note():
    steps = build_funnel_steps(
        events=5,
        leads=7,
        contact=2,
        response=1,
        meeting=0,
        opportunity=0,
        manual_leads=2,
    )
    keys = [s.key for s in steps]
    assert keys == ["event", "lead", "contact", "response", "meeting", "opportunity"]
    assert steps[0].count == 5
    assert steps[1].count == 7
    assert steps[0].note and "manual" in steps[0].note.lower()
    assert steps[1].note and "2" in steps[1].note


def test_preset_window_for_funnel():
    w = normalize_time_window(preset="last_7_days", today=date(2026, 6, 14))
    assert w.end == date(2026, 6, 14)
