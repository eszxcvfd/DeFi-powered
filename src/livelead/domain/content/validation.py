"""Generation request validation."""

from livelead.domain.content.models import ContentGenerationSettings, ContentPlatform, ContentType


def validate_settings(settings: ContentGenerationSettings) -> list[str]:
    errors: list[str] = []
    if settings.variant_count < 1 or settings.variant_count > 5:
        errors.append("variant_count must be between 1 and 5")
    if not settings.language.strip():
        errors.append("language is required")
    if len(settings.cta) > 200:
        errors.append("cta too long")
    try:
        ContentType(settings.content_type.value if hasattr(settings.content_type, "value") else settings.content_type)
        ContentPlatform(settings.platform.value if hasattr(settings.platform, "value") else settings.platform)
    except ValueError:
        errors.append("invalid content_type or platform")
    return errors