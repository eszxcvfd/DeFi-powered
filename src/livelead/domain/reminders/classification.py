"""Due versus overdue classification (US-013)."""

from datetime import date

from livelead.domain.reminders.models import ReminderState


def classify_reminder_state(due_date: date, *, today: date | None = None) -> ReminderState:
    ref = today or date.today()
    if due_date < ref:
        return ReminderState.OVERDUE
    if due_date == ref:
        return ReminderState.DUE
    return ReminderState.SCHEDULED


def is_actionable_queue_state(state: ReminderState) -> bool:
    return state in (ReminderState.SCHEDULED, ReminderState.DUE, ReminderState.OVERDUE)


def may_complete(state: ReminderState) -> bool:
    return is_actionable_queue_state(state)


def may_reschedule(state: ReminderState) -> bool:
    return state != ReminderState.COMPLETED
