from datetime import UTC, datetime

import pytest

from livelead.domain.discovery.schedule_recurrence import compute_next_run, parse_recurrence
from livelead.domain.discovery.schedule_state import ScheduleEnabledState, should_skip_overlap


def test_daily_next_run_same_day_if_before_slot():
    spec = parse_recurrence({"kind": "daily", "timezone": "UTC", "hour": 15, "minute": 30})
    after = datetime(2026, 6, 16, 10, 0, tzinfo=UTC)
    nxt = compute_next_run(spec, after=after)
    assert nxt.hour == 15 and nxt.minute == 30


def test_weekly_recurrence_summary():
    spec = parse_recurrence(
        {"kind": "weekly", "timezone": "UTC", "hour": 9, "minute": 0, "day_of_week": 2}
    )
    assert "Wed" in spec.summary()


def test_restricted_cron_rejects_wildcard_hour():
    with pytest.raises(ValueError):
        parse_recurrence({"kind": "cron", "timezone": "UTC", "cron_expression": "* 9 * * *"})


def test_overlap_skip_while_running():
    assert should_skip_overlap(active_job_status="running") is True
    assert should_skip_overlap(active_job_status="succeeded") is False


def test_schedule_may_dispatch_only_enabled():
    from livelead.domain.discovery.schedule_state import schedule_may_dispatch

    assert schedule_may_dispatch(ScheduleEnabledState.ENABLED.value) is True
    assert schedule_may_dispatch(ScheduleEnabledState.PAUSED.value) is False