"""Schema validation for discovery copilot payloads (US-037)."""

from __future__ import annotations

from livelead.domain.discovery_copilot.models import (
    CopilotClaim,
    CopilotEvidence,
    CopilotRiskFlag,
    DiscoveryCopilotStructuredResponse,
)


class CopilotSchemaError(ValueError):
    pass


def _require_list(name: str, value: object) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise CopilotSchemaError(f"{name} must be a list")
    return value


def validate_structured_response(raw: dict) -> DiscoveryCopilotStructuredResponse:
    if not isinstance(raw, dict):
        raise CopilotSchemaError("response must be an object")

    claims_raw = _require_list("claims", raw.get("claims"))
    claims: list[CopilotClaim] = []
    for item in claims_raw:
        if not isinstance(item, dict) or not str(item.get("text", "")).strip():
            raise CopilotSchemaError("each claim requires text")
        conf = item.get("confidence")
        if conf is not None and not isinstance(conf, (int, float)):
            raise CopilotSchemaError("claim confidence must be numeric")
        claims.append(
            CopilotClaim(text=str(item["text"]).strip(), confidence=float(conf) if conf is not None else None)
        )

    evidence_raw = _require_list("evidence", raw.get("evidence"))
    evidence: list[CopilotEvidence] = []
    for item in evidence_raw:
        if not isinstance(item, dict) or not str(item.get("summary", "")).strip():
            raise CopilotSchemaError("each evidence item requires summary")
        evidence.append(
            CopilotEvidence(
                summary=str(item["summary"]).strip(),
                source_ref=str(item["source_ref"]).strip() if item.get("source_ref") else None,
            )
        )

    confidence = raw.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        raise CopilotSchemaError("confidence must be numeric")
    confidence = float(confidence)
    if confidence < 0 or confidence > 1:
        raise CopilotSchemaError("confidence must be between 0 and 1")

    assumptions = [str(a).strip() for a in _require_list("assumptions", raw.get("assumptions")) if str(a).strip()]

    risk_raw = _require_list("risk_flags", raw.get("risk_flags"))
    risk_flags: list[CopilotRiskFlag] = []
    for item in risk_raw:
        if not isinstance(item, dict):
            raise CopilotSchemaError("risk_flags must be objects")
        code = str(item.get("code", "")).strip()
        message = str(item.get("message", "")).strip()
        if not code or not message:
            raise CopilotSchemaError("risk_flags require code and message")
        risk_flags.append(CopilotRiskFlag(code=code, message=message))

    framing = [
        str(x).strip()
        for x in _require_list("proposed_query_framing", raw.get("proposed_query_framing"))
        if str(x).strip()
    ]
    source_ids = [
        str(x).strip()
        for x in _require_list("recommended_source_ids", raw.get("recommended_source_ids"))
        if str(x).strip()
    ]

    if not claims:
        raise CopilotSchemaError("at least one claim is required")

    return DiscoveryCopilotStructuredResponse(
        claims=claims,
        evidence=evidence,
        confidence=confidence,
        assumptions=assumptions,
        risk_flags=risk_flags,
        proposed_query_framing=framing,
        recommended_source_ids=source_ids,
        provider_id=str(raw.get("provider_id", "deterministic-discovery-copilot-v1")),
        model_id=str(raw.get("model_id", "grounded-template-v1")),
    )


def response_to_dict(resp: DiscoveryCopilotStructuredResponse) -> dict:
    return {
        "claims": [{"text": c.text, "confidence": c.confidence} for c in resp.claims],
        "evidence": [{"summary": e.summary, "source_ref": e.source_ref} for e in resp.evidence],
        "confidence": resp.confidence,
        "assumptions": list(resp.assumptions),
        "risk_flags": [{"code": r.code, "message": r.message} for r in resp.risk_flags],
        "proposed_query_framing": list(resp.proposed_query_framing),
        "recommended_source_ids": list(resp.recommended_source_ids),
        "provider_id": resp.provider_id,
        "model_id": resp.model_id,
    }