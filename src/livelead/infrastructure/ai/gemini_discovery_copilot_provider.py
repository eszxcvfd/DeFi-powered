"""Google AI Studio (Gemini) discovery copilot provider."""

from __future__ import annotations

import json
import logging
import re

from livelead.domain.discovery_copilot.normalize import normalize_provider_payload
from livelead.domain.discovery_copilot.schema import (
    CopilotSchemaError,
    validate_structured_response,
)
from livelead.infrastructure.ai.discovery_copilot_provider import CopilotCampaignContext

logger = logging.getLogger("livelead.discovery_copilot.gemini")

_JSON_SCHEMA_HINT = """
Return ONLY valid JSON (no markdown) with this shape:
{
  "claims": [{"text": string, "confidence": number|null}],
  "evidence": [{"summary": string, "source_ref": string|null}],
  "confidence": number between 0 and 1,
  "assumptions": [string],
  "risk_flags": [{"code": string, "message": string}],
  "proposed_query_framing": [string],
  "recommended_source_ids": [string]
}
Use only the campaign context below. Do not invent secrets or external facts.
If uncertain, lower confidence and add risk_flags (e.g. low_confidence, weak_evidence).
recommended_source_ids must be a subset of the provided runnable source IDs.
You MUST include at least one non-empty claim in "claims".
"""


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


class GeminiDiscoveryCopilotProvider:
    provider_id = "google-ai-studio-gemini"
    model_id: str

    def __init__(self, *, api_key: str, model_id: str) -> None:
        self._api_key = api_key
        self.model_id = model_id

    def respond(self, question: str, ctx: CopilotCampaignContext):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError(
                "Install Google GenAI SDK: pip install 'google-genai>=1.0.0' "
                "(or pip install -e '.[ai]')"
            ) from exc

        context_block = {
            "campaign_id": ctx.campaign_id,
            "campaign_name": ctx.campaign_name,
            "target_industry": ctx.target_industry,
            "positive_keywords": ctx.positive_keywords,
            "runnable_source_ids": ctx.runnable_source_ids,
            "runnable_source_labels": ctx.runnable_source_labels,
        }
        prompt = (
            "You are a discovery planning copilot for LiveLead. "
            "Answer the user's discovery question using ONLY the JSON context.\n\n"
            f"Context:\n{json.dumps(context_block, ensure_ascii=False)}\n\n"
            f"Question:\n{question.strip()}\n\n"
            f"{_JSON_SCHEMA_HINT}"
        )

        client = genai.Client(api_key=self._api_key)
        response = client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.4,
            ),
        )
        raw_text = getattr(response, "text", None) or ""
        if not raw_text and response.candidates:
            parts = response.candidates[0].content.parts
            raw_text = "".join(getattr(p, "text", "") or "" for p in parts)

        try:
            payload = _extract_json(raw_text)
        except json.JSONDecodeError as exc:
            logger.warning("gemini_json_parse_failed len=%s", len(raw_text))
            raise CopilotSchemaError("provider returned invalid JSON") from exc

        payload = normalize_provider_payload(
            payload, campaign_name=ctx.campaign_name, question=question
        )
        structured = validate_structured_response(payload)
        allowed = set(ctx.runnable_source_ids)
        filtered = [sid for sid in structured.recommended_source_ids if sid in allowed]
        if structured.recommended_source_ids and not filtered:
            filtered = list(ctx.runnable_source_ids)[:3]

        from livelead.domain.discovery_copilot.models import DiscoveryCopilotStructuredResponse

        return DiscoveryCopilotStructuredResponse(
            claims=structured.claims,
            evidence=structured.evidence,
            confidence=structured.confidence,
            assumptions=structured.assumptions,
            risk_flags=structured.risk_flags,
            proposed_query_framing=structured.proposed_query_framing,
            recommended_source_ids=filtered,
            provider_id=self.provider_id,
            model_id=self.model_id,
        )