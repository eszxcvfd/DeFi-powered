from datetime import date

from livelead.domain.reminders.classification import (
    classify_reminder_state,
    may_complete,
    may_reschedule,
)
from livelead.domain.reminders.models import ReminderState


def test_classify_overdue():
    assert classify_reminder_state(date(2020, 1, 1), today=date(2026, 6, 14)) == ReminderState.OVERDUE


def test_classify_due_today():
    today = date(2026, 6, 14)
    assert classify_reminder_state(today, today=today) == ReminderState.DUE


def test_classify_scheduled_future():
    today = date(2026, 6, 14)
    assert classify_reminder_state(date(2026, 7, 1), today=today) == ReminderState.SCHEDULED


def test_may_complete_open_states():
    assert may_complete(ReminderState.DUE)
    assert not may_complete(ReminderState.COMPLETED)


def test_may_reschedule_not_completed():
    assert may_reschedule(ReminderState.OVERDUE)
    assert not may_reschedule(ReminderState.COMPLETED)