"""Content generation provider — infrastructure implementation."""

from datetime import UTC, datetime

from livelead.domain.content.models import (
    CONTENT_TEMPLATE_VERSION,
    DEFAULT_PROVIDER,
    ContentContextPreview,
    ContentGenerationSettings,
)


class DeterministicContentProvider:
    provider_id = DEFAULT_PROVIDER
    model_id = "deterministic-template-v1"

    def generate_variants(
        self,
        ctx: ContentContextPreview,
        settings: ContentGenerationSettings,
    ) -> list[str]:
        variants: list[str] = []
        tones = ("professional", "warm", "concise")
        for i in range(settings.variant_count):
            tone = settings.tone if i == 0 else tones[i % len(tones)]
            opening = {
                "outreach": "Hi — I noticed",
                "follow_up": "Following up on",
                "event_intro": "Quick note about",
                "value_note": "Sharing a resource related to",
            }.get(settings.content_type.value, "Hi —")
            platform_hint = {
                "email": "email",
                "linkedin": "LinkedIn message",
                "slack": "Slack note",
            }.get(settings.platform.value, "message")
            body = (
                f"{opening} {ctx.event_title}.\n\n"
                f"Given your focus on {ctx.campaign_focus}, this {ctx.audience_summary} "
                f"session could be useful ({ctx.score_summary}). "
                f"We prepared {ctx.plan_task_count} engagement tasks — this {platform_hint} "
                f"is a {tone} {settings.content_type.value.replace('_', ' ')} draft (variant {i + 1}).\n\n"
                f"CTA: {settings.cta}\n\n"
                f"[Draft only — not approved or sent. Template {CONTENT_TEMPLATE_VERSION} @ {datetime.now(UTC).isoformat()}]"
            )
            variants.append(body)
        return variants
