"""Default lead identity from event context (US-012+)."""

from __future__ import annotations


def lead_identity_from_event(
    *,
    canonical_title: str,
    organizer: str = "",
    region: str = "",
    source_url: str = "",
    description: str = "",
) -> dict[str, str]:
    """Build distinguishable lead fields: title-led name, organizer as company, context in notes."""
    title = (canonical_title or "").strip()
    org = (organizer or "").strip()
    reg = (region or "").strip()

    display_name = title[:120] if title else (org[:120] if org else "Event lead")
    company = org if org else ""

    # Avoid duplicate-looking cells when mock sets organizer = "Org {domain}" for every event.
    if (
        company
        and display_name.lower().startswith(company.lower())
        and len(display_name) > len(company) + 3
    ):
        pass  # display is title, company is org — good
    elif company and display_name.lower() == company.lower():
        if title:
            display_name = title[:120]
        elif reg:
            display_name = f"{company} ({reg})"[:120]

    lead_title = "Event prospect"
    if reg:
        lead_title = f"Event · {reg}"

    note_parts = []
    if title:
        note_parts.append(f"Event: {title}")
    if org:
        note_parts.append(f"Organizer: {org}")
    if reg:
        note_parts.append(f"Region: {reg}")
    if source_url:
        note_parts.append(f"Source: {source_url[:200]}")
    notes = "\n".join(note_parts)

    return {
        "display_name": display_name,
        "company": company,
        "title": lead_title,
        "notes": notes,
        "interests": (description or "")[:300],
    }
