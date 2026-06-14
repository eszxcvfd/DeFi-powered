from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.content.models import GeneratedContentDraft
from livelead.infrastructure.db.content_mappers import (
    draft_to_flags_json,
    row_to_draft,
    settings_to_json,
)
from livelead.infrastructure.db.models import GeneratedContentDraftRow


class ContentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_event(self, event_id: UUID) -> list[GeneratedContentDraft]:
        result = await self._session.execute(
            select(GeneratedContentDraftRow)
            .where(GeneratedContentDraftRow.event_id == str(event_id))
            .order_by(GeneratedContentDraftRow.created_at.desc(), GeneratedContentDraftRow.variant_index)
        )
        return [row_to_draft(r) for r in result.scalars().all()]

    async def add_drafts(self, drafts: list[GeneratedContentDraft]) -> list[GeneratedContentDraft]:
        for d in drafts:
            assert d.metadata
            row = GeneratedContentDraftRow(
                id=str(d.id),
                event_id=str(d.event_id),
                campaign_id=str(d.campaign_id),
                engagement_plan_id=str(d.engagement_plan_id) if d.engagement_plan_id else None,
                variant_index=d.variant_index,
                lifecycle=d.review_status.value,
                settings_json=settings_to_json(d.settings),
                body_text=d.body_text,
                risk_flags_json=draft_to_flags_json(d),
                provider=d.metadata.provider,
                model=d.metadata.model,
                prompt_template_version=d.metadata.prompt_template_version,
                input_context_summary=d.metadata.input_context_summary,
                generated_at=d.metadata.generated_at,
                last_editor=d.metadata.last_editor,
                body_revision=d.body_revision,
                reviewer_assignee=d.reviewer_assignee,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            self._session.add(row)
        await self._session.flush()
        return await self.list_for_event(drafts[0].event_id)

    async def get_draft(self, draft_id: UUID, event_id: UUID) -> GeneratedContentDraft | None:
        result = await self._session.execute(
            select(GeneratedContentDraftRow).where(
                GeneratedContentDraftRow.id == str(draft_id),
                GeneratedContentDraftRow.event_id == str(event_id),
            )
        )
        row = result.scalars().first()
        return row_to_draft(row) if row else None

    async def update_body(
        self,
        draft_id: UUID,
        event_id: UUID,
        body_text: str,
        *,
        last_editor: str,
        risk_flags_json: str,
    ) -> GeneratedContentDraft | None:
        result = await self._session.execute(
            select(GeneratedContentDraftRow).where(
                GeneratedContentDraftRow.id == str(draft_id),
                GeneratedContentDraftRow.event_id == str(event_id),
            )
        )
        row = result.scalars().first()
        if not row:
            return None
        now = datetime.now(UTC)
        row.body_text = body_text
        row.risk_flags_json = risk_flags_json
        row.last_editor = last_editor
        row.body_revision = (getattr(row, "body_revision", 1) or 1) + 1
        if row.lifecycle in ("approved", "rejected", "in_review"):
            row.lifecycle = "draft"
        row.updated_at = now
        self._session.add(row)
        await self._session.flush()
        return row_to_draft(row)