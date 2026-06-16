"""Normalize provider JSON before schema validation (US-037)."""

from __future__ import annotations


def _as_list(value: object) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _coerce_claims(raw: dict) -> list[dict]:
    claims_in = raw.get("claims")
    if claims_in is None and "claim" in raw:
        claims_in = raw.get("claim")
    out: list[dict] = []
    for item in _as_list(claims_in):
        if isinstance(item, str) and item.strip():
            out.append({"text": item.strip(), "confidence": raw.get("confidence")})
            continue
        if isinstance(item, dict):
            text = (
                item.get("text")
                or item.get("claim")
                or item.get("summary")
                or item.get("statement")
            )
            if str(text or "").strip():
                out.append(
                    {
                        "text": str(text).strip(),
                        "confidence": item.get("confidence"),
                    }
                )
    if out:
        return out

    for key in ("summary", "answer", "recommendation", "plan"):
        blob = raw.get(key)
        if isinstance(blob, str) and blob.strip():
            return [{"text": blob.strip(), "confidence": raw.get("confidence")}]
        if isinstance(blob, dict) and str(blob.get("text", "")).strip():
            return [{"text": str(blob["text"]).strip(), "confidence": blob.get("confidence")}]

    framing = _as_list(raw.get("proposed_query_framing"))
    if framing:
        text = f"Prioritize discovery queries: {', '.join(str(x) for x in framing[:5])}."
        return [{"text": text, "confidence": raw.get("confidence", 0.5)}]

    return []


def _coerce_evidence(raw: dict) -> list[dict]:
    ev = raw.get("evidence")
    out: list[dict] = []
    for item in _as_list(ev):
        if isinstance(item, str) and item.strip():
            out.append({"summary": item.strip(), "source_ref": "campaign.context"})
            continue
        if isinstance(item, dict):
            summary = item.get("summary") or item.get("text") or item.get("detail")
            if str(summary or "").strip():
                out.append(
                    {
                        "summary": str(summary).strip(),
                        "source_ref": item.get("source_ref") or item.get("source"),
                    }
                )
    return out


def _coerce_risk_flags(raw: dict) -> list[dict]:
    flags = raw.get("risk_flags") or raw.get("risks") or raw.get("risk")
    out: list[dict] = []
    for item in _as_list(flags):
        if isinstance(item, str) and item.strip():
            out.append({"code": "provider_note", "message": item.strip()})
            continue
        if isinstance(item, dict):
            code = item.get("code") or item.get("type") or "provider_note"
            message = item.get("message") or item.get("text") or item.get("detail")
            if str(message or "").strip():
                out.append({"code": str(code).strip(), "message": str(message).strip()})
    return out


def normalize_provider_payload(raw: dict, *, campaign_name: str, question: str) -> dict:
    """Map common Gemini / LLM JSON variants into the strict copilot schema shape."""
    if not isinstance(raw, dict):
        return {
            "claims": [
                {
                    "text": (
                        f"Discovery guidance for '{campaign_name}' based on your question "
                        f"(provider returned non-object JSON)."
                    ),
                    "confidence": 0.4,
                }
            ],
            "evidence": [],
            "confidence": 0.4,
            "assumptions": ["Response was normalized after incomplete provider output."],
            "risk_flags": [
                {
                    "code": "weak_evidence",
                    "message": "Provider payload required normalization; review before use.",
                }
            ],
            "proposed_query_framing": [],
            "recommended_source_ids": [],
        }

    claims = _coerce_claims(raw)
    if not claims:
        claims = [
            {
                "text": (
                    f"For campaign '{campaign_name}', refine discovery using campaign keywords "
                    f"and pinned sources to address: {question.strip()[:200]}"
                ),
                "confidence": float(raw.get("confidence", 0.45))
                if isinstance(raw.get("confidence"), (int, float))
                else 0.45,
            }
        ]

    confidence = raw.get("confidence", 0.5)
    if not isinstance(confidence, (int, float)):
        confidence = 0.5
    confidence = max(0.0, min(1.0, float(confidence)))

    framing = [
        str(x).strip()
        for x in _as_list(raw.get("proposed_query_framing") or raw.get("query_framing") or raw.get("queries"))
        if str(x).strip()
    ]

    assumptions = [
        str(a).strip()
        for a in _as_list(raw.get("assumptions") or raw.get("assumption"))
        if str(a).strip()
    ]
    if not assumptions:
        assumptions = ["Grounded in campaign criteria and runnable sources only."]

    source_ids = [
        str(x).strip()
        for x in _as_list(
            raw.get("recommended_source_ids")
            or raw.get("source_ids")
            or raw.get("recommended_sources")
        )
        if str(x).strip()
    ]

    risk_flags = _coerce_risk_flags(raw)
    if not claims[0].get("text"):
        risk_flags.append(
            {
                "code": "low_confidence",
                "message": "Fallback claim synthesized because provider omitted claims.",
            }
        )

    return {
        "claims": claims,
        "evidence": _coerce_evidence(raw),
        "confidence": confidence,
        "assumptions": assumptions,
        "risk_flags": risk_flags,
        "proposed_query_framing": framing,
        "recommended_source_ids": source_ids,
        "provider_id": raw.get("provider_id"),
        "model_id": raw.get("model_id"),
    }