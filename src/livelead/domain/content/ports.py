"""Provider port — implemented in infrastructure."""

from typing import Protocol

from livelead.domain.content.models import ContentContextPreview, ContentGenerationSettings


class ContentProviderPort(Protocol):
    provider_id: str
    model_id: str

    def generate_variants(
        self,
        ctx: ContentContextPreview,
        settings: ContentGenerationSettings,
    ) -> list[str]: ...