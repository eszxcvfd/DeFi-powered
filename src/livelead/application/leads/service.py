"""Lead pipeline application service (US-012)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.reminders.service import ReminderService
from livelead.domain.content.models import ContentUsageStatus
from livelead.domain.leads.event_defaults import lead_identity_from_event
from livelead.domain.leads.models import LeadActivityKind, LeadOriginKind, LeadRecord, LeadStage
from livelead.domain.leads.outcomes import (
    OUTCOME_STAGE_HINT,
    OutcomeType,
    derive_latest_outcome,
    may_record_outcome,
)
from livelead.domain.leads.validation import (
    find_duplicate,
    hash_email,
    may_transition_stage,
    rejects_sensitive_inference,
    validate_origin,
)
from livelead.infrastructure.db.repositories.events import EventRepository
from livelead.infrastructure.db.repositories.leads import (
    LeadActivityRepository,
    LeadRepository,
    new_lead_row,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CreateLeadInput:
    display_name: str
    company: str = ""
    title: str = ""
    public_url: str = ""
    discovery_source: str = ""
    event_id: UUID | None = None
    campaign_id: UUID | None = None
    interests: str = ""
    pain_points: str = ""
    owner: str = ""
    lawful_basis_note: str = ""
    follow_up_date: date | None = None
    notes: str = ""
    manual_entry_note: str = ""
    origin_kind: LeadOriginKind = LeadOriginKind.EVENT
    email: str = ""
    external_id: str = ""


class LeadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._leads = LeadRepository(session)
        self._activity = LeadActivityRepository(session)
        self._events = EventRepository(session)

    async def event_context_for_leads(self, organization_id: UUID, leads: list[LeadRecord]) -> dict:
        out: dict = {}
        for lead in leads:
            if not lead.event_id:
                continue
            event = await self._events.get(lead.event_id, organization_id)
            if not event:
                continue
            out[lead.id] = {
                "event_title": event.canonical_title[:100],
                "region": event.region or "",
            }
        return out

    async def list_leads(
        self,
        organization_id: UUID,
        *,
        owner: str | None = None,
        campaign_id: UUID | None = None,
        discovery_source: str | None = None,
        due_before: date | None = None,
    ) -> list[LeadRecord]:
        return await self._leads.list_for_org(
            organization_id,
            owner=owner,
            campaign_id=campaign_id,
            discovery_source=discovery_source,
            due_before=due_before,
        )

    async def get_detail(self, lead_id: UUID, organization_id: UUID):
        lead = await self._leads.get(lead_id, organization_id)
        if not lead:
            return None
        history = await self._activity.list_for_lead(lead_id)
        return lead, history

    async def linked_summary_for_event(self, event_id: UUID, organization_id: UUID):
        linked = await self._leads.list_by_event(event_id, organization_id)
        return {
            "linked_count": len(linked),
            "linked_lead_ids": [str(lead.id) for lead in linked],
            "has_linked_lead": len(linked) > 0,
        }

    async def create_lead(
        self, organization_id: UUID, actor: str, data: CreateLeadInput
    ) -> LeadRecord:
        origin_err = validate_origin(
            origin_kind=data.origin_kind,
            event_id=str(data.event_id) if data.event_id else None,
            manual_entry_note=data.manual_entry_note,
            discovery_source=data.discovery_source,
        )
        if origin_err:
            raise ValueError(origin_err)

        sens = rejects_sensitive_inference(
            data.notes,
            data.pain_points,
            data.interests,
            data.manual_entry_note,
        )
        if sens:
            raise ValueError(sens)

        campaign_id = data.campaign_id
        discovery_source = data.discovery_source
        display_name = (data.display_name or "").strip()
        company = data.company or ""
        title = data.title or ""
        notes = data.notes or ""
        interests = data.interests or ""
        event = None
        if data.origin_kind == LeadOriginKind.EVENT and data.event_id:
            event = await self._events.get(data.event_id, organization_id)
            if not event:
                raise ValueError("event not found")
            campaign_id = campaign_id or event.campaign_id
            if not discovery_source.strip():
                discovery_source = "event"
            defaults = lead_identity_from_event(
                canonical_title=event.canonical_title,
                organizer=event.organizer,
                region=event.region,
                source_url=event.source_url,
                description=event.description,
            )
            generic = (
                display_name.lower() == (company or "").strip().lower()
                or display_name.lower() == (event.organizer or "").strip().lower()
                or not notes.strip()
            )
            if generic or not title.strip():
                display_name = defaults["display_name"] if generic else display_name
                company = defaults["company"] if generic else company
                title = defaults["title"] if not title.strip() else title
                if not notes.strip():
                    notes = defaults["notes"]
                if not interests.strip():
                    interests = defaults["interests"]

        if not display_name:
            raise ValueError("display_name is required")

        email_hash = hash_email(data.email)
        candidate = {
            "public_url": data.public_url,
            "external_id": data.external_id,
            "email_hash": email_hash,
            "display_name": display_name,
            "company": company,
            "event_id": str(data.event_id) if data.event_id else None,
        }
        existing = await self._leads.list_all_for_org(organization_id)
        dup = find_duplicate(candidate, existing)
        if dup:
            raise ValueError(f"duplicate lead: {dup.reason}")

        row = new_lead_row(
            organization_id=str(organization_id),
            campaign_id=str(campaign_id) if campaign_id else None,
            display_name=display_name,
            company=company,
            title=title,
            public_url=data.public_url,
            discovery_source=discovery_source,
            event_id=str(data.event_id) if data.event_id else None,
            interests=interests,
            pain_points=data.pain_points,
            owner=data.owner or actor,
            stage=LeadStage.NEWLY_DISCOVERED.value,
            lawful_basis_note=data.lawful_basis_note,
            follow_up_date=data.follow_up_date.isoformat() if data.follow_up_date else None,
            notes=notes,
            manual_entry_note=data.manual_entry_note,
            origin_kind=data.origin_kind.value,
            email_hash=email_hash,
            external_id=data.external_id,
            created_by=actor,
        )
        lead = await self._leads.insert(row)
        await self._activity.append(
            lead_id=lead.id,
            kind=LeadActivityKind.CREATED.value,
            actor=actor,
            body="Lead created",
            to_stage=lead.stage.value,
        )
        logger.info(
            "lead_created lead_id=%s event_id=%s actor=%s origin=%s",
            lead.id,
            lead.event_id,
            actor,
            lead.origin_kind.value,
        )
        await ReminderService(self._session).sync_from_lead(
            organization_id,
            lead.id,
            owner=lead.owner,
            follow_up_date=lead.follow_up_date,
            actor=actor,
        )
        return lead

    async def update_lead(
        self,
        lead_id: UUID,
        organization_id: UUID,
        actor: str,
        *,
        owner: str | None = None,
        notes: str | None = None,
        follow_up_date: date | None | object = ...,
        stage: LeadStage | None = None,
        activity_note: str | None = None,
        title: str | None = None,
        company: str | None = None,
    ) -> LeadRecord | None:
        lead = await self._leads.get(lead_id, organization_id)
        if not lead:
            return None

        fields: dict[str, object] = {}
        if owner is not None:
            fields["owner"] = owner
        if notes is not None:
            fields["notes"] = notes
        if title is not None:
            fields["title"] = title
        if company is not None:
            fields["company"] = company
        if follow_up_date is not ...:
            fields["follow_up_date"] = follow_up_date.isoformat() if follow_up_date else None

        stage_from = lead.stage
        if stage is not None:
            if not may_transition_stage(lead.stage, stage):
                raise ValueError("invalid stage transition")
            fields["stage"] = stage.value

        if not fields and not activity_note:
            return lead

        updated = (
            await self._leads.save_fields(lead_id, organization_id, **fields) if fields else lead
        )

        if activity_note and activity_note.strip():
            await self._activity.append(
                lead_id=lead_id,
                kind=LeadActivityKind.NOTE.value,
                actor=actor,
                body=activity_note.strip(),
            )
            logger.info("lead_note lead_id=%s actor=%s", lead_id, actor)

        if stage is not None and stage != stage_from and updated:
            await self._activity.append(
                lead_id=lead_id,
                kind=LeadActivityKind.STAGE_CHANGED.value,
                actor=actor,
                body=f"Stage changed to {stage.value}",
                from_stage=stage_from.value,
                to_stage=stage.value,
            )
            logger.info(
                "lead_stage_change lead_id=%s actor=%s from=%s to=%s",
                lead_id,
                actor,
                stage_from.value,
                stage.value,
            )

        if fields and not activity_note and stage is None:
            await self._activity.append(
                lead_id=lead_id,
                kind=LeadActivityKind.FIELD_UPDATED.value,
                actor=actor,
                body="Lead details updated",
            )

        refreshed = await self._leads.get(lead_id, organization_id)
        if refreshed and follow_up_date is not ...:
            await ReminderService(self._session).sync_from_lead(
                organization_id,
                lead_id,
                owner=refreshed.owner,
                follow_up_date=refreshed.follow_up_date,
                actor=actor,
            )
        return refreshed

    async def list_activity(self, lead_id: UUID):
        return await self._activity.list_for_lead(lead_id)

    def latest_outcome_from_history(self, history: list):
        return derive_latest_outcome(history)

    async def record_outcome(
        self,
        lead_id: UUID,
        organization_id: UUID,
        actor: str,
        *,
        outcome_type: OutcomeType,
        occurred_at: datetime | None = None,
        notes: str = "",
        linked_content_draft_id: UUID | None = None,
        linked_event_id: UUID | None = None,
        content_validator=None,
    ) -> LeadRecord | None:
        lead = await self._leads.get(lead_id, organization_id)
        if not lead:
            return None

        history = await self._activity.list_for_lead(lead_id)
        guard = may_record_outcome(lead, outcome_type, history=history)
        if guard:
            raise ValueError(guard)

        if linked_content_draft_id:
            if not linked_event_id:
                linked_event_id = lead.event_id
            if not linked_event_id:
                raise ValueError("linked content requires lead event_id or linked_event_id")
            if content_validator is None:
                raise ValueError("content validation required for linked content")
            draft = await content_validator(
                linked_event_id, linked_content_draft_id, organization_id
            )
            if not draft:
                raise ValueError("linked content not found")
            if draft.usage_status != ContentUsageStatus.USED:
                raise ValueError("linked content must be marked as used")

        when = occurred_at or datetime.now(UTC)
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)

        label = outcome_type.value.replace("_", " ")
        body = (notes or "").strip() or f"Recorded {label} outcome"
        await self._activity.append(
            lead_id=lead_id,
            kind=LeadActivityKind.OUTCOME_RECORDED.value,
            actor=actor,
            body=body,
            outcome_type=outcome_type.value,
            occurred_at=when,
            linked_content_draft_id=str(linked_content_draft_id) if linked_content_draft_id else "",
        )

        hint_stage = OUTCOME_STAGE_HINT.get(outcome_type)
        if hint_stage and lead.stage != hint_stage:
            from livelead.domain.leads.validation import may_transition_stage

            if may_transition_stage(lead.stage, hint_stage):
                await self._leads.save_fields(lead_id, organization_id, stage=hint_stage.value)
                await self._activity.append(
                    lead_id=lead_id,
                    kind=LeadActivityKind.STAGE_CHANGED.value,
                    actor=actor,
                    body=f"Stage advanced to {hint_stage.value} after outcome",
                    from_stage=lead.stage.value,
                    to_stage=hint_stage.value,
                )

        logger.info(
            "lead_outcome_recorded lead_id=%s type=%s actor=%s content=%s occurred_at=%s",
            lead_id,
            outcome_type.value,
            actor,
            linked_content_draft_id,
            when.isoformat(),
        )
        return await self._leads.get(lead_id, organization_id)
