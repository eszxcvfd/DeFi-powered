import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audience.service import AudienceService
from livelead.application.engagement.service import EngagementService
from livelead.domain.content.export import export_csv, export_markdown
from livelead.domain.content.generator import generate_drafts
from livelead.domain.content.handoff import (
    HandoffAction,
    can_mark_used,
    may_handoff_content,
    normalize_export_format,
)
from livelead.domain.content.models import (
    ContentContextPreview,
    ContentGenerationSettings,
    ContentHandoffRecord,
    ContentPlatform,
    ContentReviewDecision,
    ContentReviewStatus,
    ContentType,
    ContentUsageStatus,
    GeneratedContentDraft,
)
from livelead.domain.content.review import actor_may_review, can_transition
from livelead.domain.content.risk import evaluate_draft_risks
from livelead.infrastructure.ai.provider import DeterministicContentProvider
from livelead.infrastructure.db.content_mappers import draft_to_flags_json
from livelead.infrastructure.db.repositories.campaigns import CampaignRepository
from livelead.infrastructure.db.repositories.content import ContentRepository
from livelead.infrastructure.db.repositories.content_handoff import ContentHandoffRepository
from livelead.infrastructure.db.repositories.content_review import ContentReviewRepository
from livelead.infrastructure.db.repositories.event_scores import EventScoreRepository
from livelead.infrastructure.db.repositories.events import EventRepository

logger = logging.getLogger("livelead.content")


class ContentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = EventRepository(session)
        self._campaigns = CampaignRepository(session)
        self._scores = EventScoreRepository(session)
        self._content = ContentRepository(session)
        self._review = ContentReviewRepository(session)
        self._handoff = ContentHandoffRepository(session)
        self._engagement = EngagementService(session)
        self._provider = DeterministicContentProvider()

    async def list_drafts(self, event_id: UUID, organization_id: UUID) -> list[GeneratedContentDraft] | None:
        if not await self._events.get(event_id, organization_id):
            return None
        return await self._content.list_for_event(event_id)

    async def preview_context(self, event_id: UUID, organization_id: UUID) -> ContentContextPreview | None:
        event = await self._events.get(event_id, organization_id)
        if not event:
            return None
        campaign = await self._campaigns.get(event.campaign_id, organization_id)
        if not campaign:
            return None
        score = await self._scores.get_current(event_id, event.campaign_id)
        audience = await AudienceService(self._session).get_or_generate(event_id, organization_id)
        plan = await self._engagement.get_plan_state(event_id, organization_id)
        from livelead.domain.content.context import build_context_preview

        return build_context_preview(event, campaign, score, audience, plan)

    async def generate(
        self,
        event_id: UUID,
        organization_id: UUID,
        settings: ContentGenerationSettings,
    ) -> tuple[ContentContextPreview | None, list[GeneratedContentDraft], list[str]]:
        event = await self._events.get(event_id, organization_id)
        if not event:
            return None, [], ["event not found"]
        campaign = await self._campaigns.get(event.campaign_id, organization_id)
        if not campaign:
            return None, [], ["campaign not found"]
        score = await self._scores.get_current(event_id, event.campaign_id)
        audience = await AudienceService(self._session).get_or_generate(event_id, organization_id)
        plan = await self._engagement.get_plan_state(event_id, organization_id)
        plan_id = plan.plan.id if plan.plan else None

        preview, drafts, errors = generate_drafts(
            event_id=event_id,
            campaign_id=event.campaign_id,
            engagement_plan_id=plan_id,
            event=event,
            campaign=campaign,
            score=score,
            audience=audience,
            plan=plan,
            settings=settings,
            provider=self._provider,
        )
        if errors:
            return preview, [], errors
        if not drafts:
            return preview, [], ["no drafts produced"]

        saved = await self._content.add_drafts(drafts)
        logger.info(
            "content_generated event_id=%s count=%s provider=%s",
            event_id,
            len(saved),
            self._provider.provider_id,
        )
        return preview, saved, []

    async def update_draft(
        self,
        event_id: UUID,
        draft_id: UUID,
        organization_id: UUID,
        body_text: str,
        *,
        editor: str = "analyst",
    ) -> GeneratedContentDraft | None:
        if not await self._events.get(event_id, organization_id):
            return None
        existing = await self._content.get_draft(draft_id, event_id)
        if not existing:
            return None
        event = await self._events.get(event_id, organization_id)
        assert event
        flags = evaluate_draft_risks(
            body_text,
            event_title=event.canonical_title,
            cta=existing.settings.cta,
        )
        draft_flags = tuple(flags)
        temp = GeneratedContentDraft(
            id=existing.id,
            event_id=existing.event_id,
            campaign_id=existing.campaign_id,
            engagement_plan_id=existing.engagement_plan_id,
            variant_index=existing.variant_index,
            review_status=existing.review_status,
            settings=existing.settings,
            body_text=body_text,
            body_revision=existing.body_revision,
            reviewer_assignee=existing.reviewer_assignee,
            risk_flags=draft_flags,
            metadata=existing.metadata,
        )
        updated = await self._content.update_body(
            draft_id,
            event_id,
            body_text,
            last_editor=editor,
            risk_flags_json=draft_to_flags_json(temp),
        )
        if updated:
            logger.info("content_draft_edited event_id=%s draft_id=%s editor=%s", event_id, draft_id, editor)
        return updated

    async def get_draft_for_org(self, draft_id: UUID, event_id: UUID, organization_id: UUID) -> GeneratedContentDraft | None:
        if not await self._events.get(event_id, organization_id):
            return None
        return await self._content.get_draft(draft_id, event_id)

    async def list_review_history(self, draft_id: UUID) -> list[ContentReviewDecision]:
        return await self._review.list_for_draft(draft_id)

    async def list_handoff_history(self, draft_id: UUID) -> list[ContentHandoffRecord]:
        return await self._handoff.list_for_draft(draft_id)

    async def record_copy_handoff(
        self,
        event_id: UUID,
        draft_id: UUID,
        organization_id: UUID,
        *,
        actor: str,
    ) -> GeneratedContentDraft | None:
        draft = await self.get_draft_for_org(draft_id, event_id, organization_id)
        if not draft:
            return None
        if not may_handoff_content(draft.review_status):
            raise ValueError("content not approved for handoff")
        await self._handoff.append(
            draft_id=draft_id,
            event_id=event_id,
            action=HandoffAction.COPY.value,
            actor=actor,
            body_revision=draft.body_revision,
        )
        logger.info("content_handoff_copy draft_id=%s actor=%s", draft_id, actor)
        return await self._content.get_draft(draft_id, event_id)

    async def export_approved(
        self,
        event_id: UUID,
        draft_id: UUID,
        organization_id: UUID,
        *,
        fmt: str,
        actor: str,
    ) -> tuple[str, str, str] | None:
        """Returns (media_type, filename, body) or None if draft missing."""
        draft = await self.get_draft_for_org(draft_id, event_id, organization_id)
        if not draft:
            return None
        if not may_handoff_content(draft.review_status):
            raise ValueError("content not approved for handoff")
        normalized = normalize_export_format(fmt)
        if not normalized:
            raise ValueError("unsupported export format")
        if normalized == "markdown":
            body = export_markdown(draft)
            media_type = "text/markdown; charset=utf-8"
            filename = f"content-{draft_id}-variant-{draft.variant_index + 1}.md"
        else:
            body = export_csv(draft)
            media_type = "text/csv; charset=utf-8"
            filename = f"content-{draft_id}-variant-{draft.variant_index + 1}.csv"
        await self._handoff.append(
            draft_id=draft_id,
            event_id=event_id,
            action=HandoffAction.EXPORT.value,
            actor=actor,
            export_format=normalized,
            body_revision=draft.body_revision,
        )
        logger.info("content_handoff_export draft_id=%s format=%s actor=%s", draft_id, normalized, actor)
        return media_type, filename, body

    async def mark_used(
        self,
        event_id: UUID,
        draft_id: UUID,
        organization_id: UUID,
        *,
        actor: str,
    ) -> GeneratedContentDraft | None:
        draft = await self.get_draft_for_org(draft_id, event_id, organization_id)
        if not draft:
            return None
        if not may_handoff_content(draft.review_status):
            raise ValueError("content not approved for handoff")
        usage = draft.usage_status
        if not can_mark_used(usage):
            raise ValueError("invalid usage transition")
        await self._handoff.set_usage_status(draft_id, event_id, ContentUsageStatus.USED)
        await self._handoff.append(
            draft_id=draft_id,
            event_id=event_id,
            action=HandoffAction.MARK_USED.value,
            actor=actor,
            body_revision=draft.body_revision,
        )
        logger.info("content_mark_used draft_id=%s actor=%s", draft_id, actor)
        return await self._content.get_draft(draft_id, event_id)

    async def submit_for_review(
        self,
        event_id: UUID,
        draft_id: UUID,
        organization_id: UUID,
        *,
        actor: str,
        assignee: str = "",
    ) -> GeneratedContentDraft | None:
        draft = await self.get_draft_for_org(draft_id, event_id, organization_id)
        if not draft:
            return None
        new = ContentReviewStatus.IN_REVIEW
        if not can_transition(draft.review_status, new):
            raise ValueError("invalid review transition")
        await self._review.set_review_status(draft_id, event_id, new, reviewer_assignee=assignee or actor)
        await self._review.append_decision(
            draft_id=draft_id,
            event_id=event_id,
            action="submit",
            from_status=draft.review_status,
            to_status=new,
            actor=actor,
            note="",
            body_revision=draft.body_revision,
        )
        logger.info("content_submit_review draft_id=%s actor=%s", draft_id, actor)
        return await self._content.get_draft(draft_id, event_id)

    async def approve_draft(
        self,
        event_id: UUID,
        draft_id: UUID,
        organization_id: UUID,
        *,
        actor: str,
        actor_role: str,
        note: str = "",
    ) -> GeneratedContentDraft | None:
        if not actor_may_review(actor_role):
            raise PermissionError("role cannot approve content")
        draft = await self.get_draft_for_org(draft_id, event_id, organization_id)
        if not draft:
            return None
        new = ContentReviewStatus.APPROVED
        if not can_transition(draft.review_status, new):
            raise ValueError("invalid review transition")
        await self._review.set_review_status(draft_id, event_id, new, reviewer_assignee=actor)
        await self._review.append_decision(
            draft_id=draft_id,
            event_id=event_id,
            action="approve",
            from_status=draft.review_status,
            to_status=new,
            actor=actor,
            note=note,
            body_revision=draft.body_revision,
        )
        logger.info("content_approved draft_id=%s actor=%s rev=%s", draft_id, actor, draft.body_revision)
        return await self._content.get_draft(draft_id, event_id)

    async def reject_draft(
        self,
        event_id: UUID,
        draft_id: UUID,
        organization_id: UUID,
        *,
        actor: str,
        actor_role: str,
        note: str = "",
    ) -> GeneratedContentDraft | None:
        if not actor_may_review(actor_role):
            raise PermissionError("role cannot reject content")
        draft = await self.get_draft_for_org(draft_id, event_id, organization_id)
        if not draft:
            return None
        new = ContentReviewStatus.REJECTED
        if not can_transition(draft.review_status, new):
            raise ValueError("invalid review transition")
        await self._review.set_review_status(draft_id, event_id, new, reviewer_assignee=actor)
        await self._review.append_decision(
            draft_id=draft_id,
            event_id=event_id,
            action="reject",
            from_status=draft.review_status,
            to_status=new,
            actor=actor,
            note=note,
            body_revision=draft.body_revision,
        )
        logger.info("content_rejected draft_id=%s actor=%s", draft_id, actor)
        return await self._content.get_draft(draft_id, event_id)

    @staticmethod
    def settings_from_payload(data: dict) -> ContentGenerationSettings:
        return ContentGenerationSettings(
            content_type=ContentType(data.get("content_type", "outreach")),
            platform=ContentPlatform(data.get("platform", "email")),
            language=data.get("language", "en"),
            tone=data.get("tone", "professional"),
            length=data.get("length", "medium"),
            market_context=data.get("market_context", ""),
            cta=data.get("cta", "Learn more"),
            variant_count=int(data.get("variant_count", 2)),
        )