from livelead.domain.events.confidence import (
    FieldTrust,
    confidence_for_new_event,
    summary_confidence,
)


def test_confidence_new_event_marks_missing_organizer():
    fields = confidence_for_new_event(has_organizer=False, has_region=True, has_starts_at=True)
    org = next(f for f in fields if f.field == "organizer")
    assert org.trust == FieldTrust.INFERRED


def test_summary_merged():
    from livelead.domain.events.confidence import confidence_after_merge

    assert summary_confidence(confidence_after_merge()) == "merged"
