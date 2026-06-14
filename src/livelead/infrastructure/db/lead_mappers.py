from datetime import date
from uuid import UUID

from livelead.domain.leads.models import (
    LeadActivityEntry,
    LeadActivityKind,
    LeadOriginKind,
    LeadRecord,
    LeadStage,
)
from livelead.infrastructure.db.models import LeadActivityRow, LeadRow


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def row_to_lead(row: LeadRow) -> LeadRecord:
    return LeadRecord(
        id=UUID(row.id),
        organization_id=UUID(row.organization_id),
        campaign_id=UUID(row.campaign_id) if row.campaign_id else None,
        display_name=row.display_name,
        company=row.company or "",
        title=row.title or "",
        public_url=row.public_url or "",
        discovery_source=row.discovery_source or "",
        event_id=UUID(row.event_id) if row.event_id else None,
        interests=row.interests or "",
        pain_points=row.pain_points or "",
        owner=row.owner or "",
        stage=LeadStage(row.stage),
        lawful_basis_note=row.lawful_basis_note or "",
        follow_up_date=_parse_date(row.follow_up_date),
        notes=row.notes or "",
        manual_entry_note=row.manual_entry_note or "",
        origin_kind=LeadOriginKind(row.origin_kind),
        email_hash=row.email_hash or "",
        external_id=row.external_id or "",
        created_by=row.created_by or "analyst",
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def row_to_activity(row: LeadActivityRow) -> LeadActivityEntry:
    return LeadActivityEntry(
        id=UUID(row.id),
        lead_id=UUID(row.lead_id),
        kind=LeadActivityKind(row.kind),
        actor=row.actor,
        body=row.body or "",
        from_stage=row.from_stage or "",
        to_stage=row.to_stage or "",
        created_at=row.created_at,
        outcome_type=getattr(row, "outcome_type", None) or "",
        occurred_at=getattr(row, "occurred_at", None),
        linked_content_draft_id=getattr(row, "linked_content_draft_id", None) or "",
    )