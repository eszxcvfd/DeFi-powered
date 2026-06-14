"""Lead origin and duplicate rules (US-012)."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

from livelead.domain.leads.models import LeadDuplicateMatch, LeadOriginKind, LeadRecord, LeadStage

_SENSITIVE_INFERENCE_MARKERS = (
    "inferred",
    "sensitive trait",
    "private contact",
    "scraped email",
)


def normalize_public_url(raw: str) -> str:
    text = (raw or "").strip().lower()
    if not text:
        return ""
    if not text.startswith(("http://", "https://")):
        text = f"https://{text}"
    parsed = urlparse(text)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").rstrip("/")
    if not host:
        return ""
    return f"{host}{path}"


def normalize_identity_key(display_name: str, company: str) -> str:
    name = re.sub(r"\s+", " ", (display_name or "").strip().lower())
    comp = re.sub(r"\s+", " ", (company or "").strip().lower())
    if not name or not comp:
        return ""
    return f"{name}|{comp}"


def hash_email(raw: str) -> str:
    email = (raw or "").strip().lower()
    if not email or "@" not in email:
        return ""
    return hashlib.sha256(email.encode("utf-8")).hexdigest()


def validate_origin(
    *,
    origin_kind: LeadOriginKind,
    event_id: str | None,
    manual_entry_note: str,
    discovery_source: str,
) -> str | None:
    if origin_kind == LeadOriginKind.EVENT:
        if not event_id:
            return "event-linked lead requires event_id"
        if not (discovery_source or "").strip():
            return "event-linked lead requires discovery_source"
        return None
    note = (manual_entry_note or "").strip()
    if not note:
        return "manual lead requires manual_entry_note"
    return None


def rejects_sensitive_inference(*texts: str) -> str | None:
    blob = " ".join(t for t in texts if t).lower()
    for marker in _SENSITIVE_INFERENCE_MARKERS:
        if marker in blob:
            return "lead creation cannot use inferred sensitive traits"
    return None


def find_duplicate(
    candidate: dict,
    existing: list[LeadRecord],
) -> LeadDuplicateMatch | None:
    url = normalize_public_url(candidate.get("public_url", ""))
    ext = (candidate.get("external_id") or "").strip().lower()
    email_h = (candidate.get("email_hash") or "").strip().lower()
    identity = normalize_identity_key(candidate.get("display_name", ""), candidate.get("company", ""))
    cand_event = candidate.get("event_id")

    for lead in existing:
        if cand_event and lead.event_id and str(lead.event_id) == str(cand_event):
            return LeadDuplicateMatch(lead.id, "duplicate event link")
        if url and normalize_public_url(lead.public_url) == url:
            return LeadDuplicateMatch(lead.id, "duplicate public_url")
        if ext and lead.external_id and lead.external_id.lower() == ext:
            return LeadDuplicateMatch(lead.id, "duplicate external_id")
        if email_h and lead.email_hash and lead.email_hash.lower() == email_h:
            return LeadDuplicateMatch(lead.id, "duplicate email_hash")
        # Event-linked leads from different events often share organizer-only fields; do not
        # block on name+company across unrelated events.
        if cand_event and lead.event_id and str(lead.event_id) != str(cand_event):
            continue
        if identity:
            other = normalize_identity_key(lead.display_name, lead.company)
            if other == identity:
                return LeadDuplicateMatch(lead.id, "duplicate display_name and company")
    return None


def may_transition_stage(current: LeadStage, target: LeadStage) -> bool:
    if current == target:
        return True
    if current == LeadStage.NOT_FIT and target != LeadStage.NOT_FIT:
        return False
    return target in LeadStage