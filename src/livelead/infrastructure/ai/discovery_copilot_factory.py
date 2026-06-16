"""Discovery copilot provider selection (US-037 + Google AI Studio)."""

from __future__ import annotations

from livelead.infrastructure.ai.discovery_copilot_provider import (
    DeterministicDiscoveryCopilotProvider,
)
from livelead.runtime.settings import AppSettings


class CopilotProviderNotConfiguredError(RuntimeError):
    pass


def build_discovery_copilot_provider(settings: AppSettings):
    mode = (settings.discovery_copilot_provider or "deterministic").strip().lower()
    if mode in ("gemini", "google", "google_ai_studio"):
        if not (settings.google_ai_studio_api_key or "").strip():
            raise CopilotProviderNotConfiguredError(
                "Set LIVELEAD_GOOGLE_AI_STUDIO_API_KEY in repo-root .env "
                "(Google AI Studio API key) and LIVELEAD_DISCOVERY_COPILOT_PROVIDER=gemini"
            )
        from livelead.infrastructure.ai.gemini_discovery_copilot_provider import (
            GeminiDiscoveryCopilotProvider,
        )

        return GeminiDiscoveryCopilotProvider(
            api_key=settings.google_ai_studio_api_key.strip(),
            model_id=settings.gemini_model,
        )
    return DeterministicDiscoveryCopilotProvider()