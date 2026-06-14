from datetime import UTC, datetime
from uuid import uuid4

from livelead.domain.content.export import export_csv, export_markdown
from livelead.domain.content.handoff import (
    can_mark_used,
    may_handoff_content,
    normalize_export_format,
)
from livelead.domain.content.models import (
    ContentGenerationSettings,
    ContentPlatform,
    ContentReviewStatus,
    ContentType,
    ContentUsageStatus,
    GeneratedContentDraft,
    GenerationMetadata,
)


def _draft(status: ContentReviewStatus) -> GeneratedContentDraft:
    now = datetime.now(UTC)
    settings = ContentGenerationSettings(
        content_type=ContentType.OUTREACH,
        platform=ContentPlatform.EMAIL,
    )
    return GeneratedContentDraft(
        id=uuid4(),
        event_id=uuid4(),
        campaign_id=uuid4(),
        engagement_plan_id=None,
        variant_index=0,
        review_status=status,
        settings=settings,
        body_text="Hello\nWorld",
        metadata=GenerationMetadata(
            provider="p",
            model="m",
            prompt_template_version="v",
            input_context_summary="internal only",
            generated_at=now,
        ),
    )


def test_may_handoff_only_approved():
    assert may_handoff_content(ContentReviewStatus.APPROVED)
    assert not may_handoff_content(ContentReviewStatus.DRAFT)


def test_can_mark_used_once():
    assert can_mark_used(ContentUsageStatus.NOT_USED)
    assert not can_mark_used(ContentUsageStatus.USED)


def test_export_formats():
    assert normalize_export_format("Markdown") == "markdown"
    assert normalize_export_format("pdf") is None


def test_export_strips_internal_context():
    d = _draft(ContentReviewStatus.APPROVED)
    md = export_markdown(d)
    assert "internal only" not in md
    assert "Hello" in md
    csv = export_csv(d)
    assert "internal only" not in csv
    assert "Hello" in csv