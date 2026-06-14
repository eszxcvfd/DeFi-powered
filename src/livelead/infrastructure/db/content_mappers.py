import json
from uuid import UUID

from livelead.domain.content.models import (
    ContentGenerationSettings,
    ContentHandoffRecord,
    ContentPlatform,
    ContentReviewDecision,
    ContentReviewStatus,
    ContentRiskFlag,
    ContentType,
    ContentUsageStatus,
    GeneratedContentDraft,
    GenerationMetadata,
    RiskFlagCode,
)
from livelead.infrastructure.db.models import (
    ContentHandoffRecordRow,
    ContentReviewDecisionRow,
    GeneratedContentDraftRow,
)


def _settings_from_json(raw: str) -> ContentGenerationSettings:
    d = json.loads(raw or "{}")
    return ContentGenerationSettings(
        content_type=ContentType(d.get("content_type", "outreach")),
        platform=ContentPlatform(d.get("platform", "email")),
        language=d.get("language", "en"),
        tone=d.get("tone", "professional"),
        length=d.get("length", "medium"),
        market_context=d.get("market_context", ""),
        cta=d.get("cta", "Learn more"),
        variant_count=int(d.get("variant_count", 2)),
    )


def settings_to_json(s: ContentGenerationSettings) -> str:
    return json.dumps(
        {
            "content_type": s.content_type.value,
            "platform": s.platform.value,
            "language": s.language,
            "tone": s.tone,
            "length": s.length,
            "market_context": s.market_context,
            "cta": s.cta,
            "variant_count": s.variant_count,
        }
    )


def row_to_draft(row: GeneratedContentDraftRow) -> GeneratedContentDraft:
    flags_raw = json.loads(row.risk_flags_json or "[]")
    flags = tuple(
        ContentRiskFlag(
            code=RiskFlagCode(f["code"]),
            message=f.get("message", ""),
            severity=f.get("severity", "warning"),
        )
        for f in flags_raw
        if isinstance(f, dict) and "code" in f
    )
    meta = GenerationMetadata(
        provider=row.provider,
        model=row.model,
        prompt_template_version=row.prompt_template_version,
        input_context_summary=row.input_context_summary,
        generated_at=row.generated_at,
        last_editor=row.last_editor or "system",
    )
    status_raw = getattr(row, "lifecycle", None) or "draft"
    rev = getattr(row, "body_revision", 1) or 1
    assignee = getattr(row, "reviewer_assignee", "") or ""
    usage_raw = getattr(row, "usage_status", None) or ContentUsageStatus.NOT_USED.value
    return GeneratedContentDraft(
        id=UUID(row.id),
        event_id=UUID(row.event_id),
        campaign_id=UUID(row.campaign_id),
        engagement_plan_id=UUID(row.engagement_plan_id) if row.engagement_plan_id else None,
        variant_index=row.variant_index,
        review_status=ContentReviewStatus(status_raw),
        body_revision=rev,
        reviewer_assignee=assignee,
        usage_status=ContentUsageStatus(usage_raw),
        settings=_settings_from_json(row.settings_json),
        body_text=row.body_text,
        risk_flags=flags,
        metadata=meta,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def row_to_handoff(row: ContentHandoffRecordRow) -> ContentHandoffRecord:
    return ContentHandoffRecord(
        id=UUID(row.id),
        draft_id=UUID(row.draft_id),
        event_id=UUID(row.event_id),
        action=row.action,
        actor=row.actor,
        export_format=row.export_format or "",
        body_revision=row.body_revision,
        created_at=row.created_at,
    )


def row_to_decision(row: ContentReviewDecisionRow) -> ContentReviewDecision:
    return ContentReviewDecision(
        id=UUID(row.id),
        draft_id=UUID(row.draft_id),
        event_id=UUID(row.event_id),
        action=row.action,
        from_status=row.from_status,
        to_status=row.to_status,
        actor=row.actor,
        note=row.note or "",
        body_revision=row.body_revision,
        created_at=row.created_at,
    )


def draft_to_flags_json(draft: GeneratedContentDraft) -> str:
    return json.dumps(
        [
            {"code": f.code.value, "message": f.message, "severity": f.severity}
            for f in draft.risk_flags
        ]
    )
