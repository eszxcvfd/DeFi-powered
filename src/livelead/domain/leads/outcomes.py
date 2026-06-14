"""Lead outcome rules (US-015)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from livelead.domain.leads.models import LeadActivityEntry, LeadActivityKind, LeadRecord, LeadStage


class OutcomeType(StrEnum):
    CONTACT = "contact"
    RESPONSE = "response"
    MEETING = "meeting"
    OPPORTUNITY = "opportunity"


OUTCOME_STAGE_HINT: dict[OutcomeType, LeadStage] = {
    OutcomeType.CONTACT: LeadStage.CONNECTED,
    OutcomeType.RESPONSE: LeadStage.RESPONDED,
    OutcomeType.MEETING: LeadStage.MEETING_SCHEDULED,
    OutcomeType.OPPORTUNITY: LeadStage.OPPORTUNITY,
}


@dataclass(frozen=True, slots=True)
class LatestLeadOutcome:
    outcome_type: OutcomeType
    occurred_at: datetime
    actor: str
    activity_id: UUID
    linked_content_draft_id: UUID | None = None
    notes: str = ""


def parse_outcome_type(raw: str) -> OutcomeType | None:
    try:
        return OutcomeType(raw.strip().lower())
    except ValueError:
        return None


def _history_has_outcome(history: list[LeadActivityEntry] | None, *types: OutcomeType) -> bool:
    if not history:
        return False
    wanted = {t.value for t in types}
    for entry in history:
        if entry.kind == LeadActivityKind.OUTCOME_RECORDED and entry.outcome_type in wanted:
            return True
    return False


def may_record_outcome(
    lead: LeadRecord,
    outcome: OutcomeType,
    *,
    history: list[LeadActivityEntry] | None = None,
) -> str | None:
    if lead.stage == LeadStage.NOT_FIT:
        return "cannot record outcomes on a not-fit lead"
    if outcome == OutcomeType.OPPORTUNITY and lead.stage in (
        LeadStage.NEWLY_DISCOVERED,
        LeadStage.WATCHED,
    ):
        if not _history_has_outcome(
            history,
            OutcomeType.CONTACT,
            OutcomeType.RESPONSE,
            OutcomeType.MEETING,
        ):
            return "opportunity outcome requires prior engagement on the lead"
    if outcome == OutcomeType.MEETING:
        if lead.stage == LeadStage.NEWLY_DISCOVERED and not _history_has_outcome(
            history, OutcomeType.CONTACT, OutcomeType.RESPONSE
        ):
            return "meeting outcome requires prior contact or outreach"
    return None


def derive_latest_outcome(history: list[LeadActivityEntry]) -> LatestLeadOutcome | None:
    for entry in history:
        if entry.kind != LeadActivityKind.OUTCOME_RECORDED or not entry.outcome_type:
            continue
        try:
            otype = OutcomeType(entry.outcome_type)
        except ValueError:
            continue
        occurred = entry.occurred_at or entry.created_at
        link = UUID(entry.linked_content_draft_id) if entry.linked_content_draft_id else None
        return LatestLeadOutcome(
            outcome_type=otype,
            occurred_at=occurred,
            actor=entry.actor,
            activity_id=entry.id,
            linked_content_draft_id=link,
            notes=entry.body,
        )
    return None
