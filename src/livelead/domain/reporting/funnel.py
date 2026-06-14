"""Funnel reporting read-model (US-016)."""

from dataclasses import dataclass
from datetime import date, datetime

FUNNEL_COHORT_RULE = (
    "Events are counted by observed_at in the selected range. "
    "Leads are counted by created_at in the range (event-linked and manual). "
    "Contact, response, meeting, and opportunity count distinct leads with at least one "
    "recorded outcome of that type whose occurred_at falls in the range."
)

FUNNEL_STEP_ORDER: tuple[tuple[str, str], ...] = (
    ("event", "Events discovered"),
    ("lead", "Leads created"),
    ("contact", "Contact outcomes"),
    ("response", "Response outcomes"),
    ("meeting", "Meeting outcomes"),
    ("opportunity", "Opportunity outcomes"),
)


@dataclass(frozen=True, slots=True)
class FunnelCohort:
    start: date
    end: date
    preset: str | None
    rule: str = FUNNEL_COHORT_RULE


@dataclass(frozen=True, slots=True)
class FunnelStep:
    key: str
    label: str
    count: int
    note: str | None = None


@dataclass(frozen=True, slots=True)
class UnattributedLeadSummary:
    manual_leads_in_cohort: int
    explanation: str


@dataclass(frozen=True, slots=True)
class FunnelFreshness:
    last_updated_at: datetime | None
    source: str


@dataclass(frozen=True, slots=True)
class FunnelReport:
    cohort: FunnelCohort
    steps: tuple[FunnelStep, ...]
    unattributed: UnattributedLeadSummary | None
    freshness: FunnelFreshness
    generated_at: datetime


def build_funnel_steps(
    *,
    events: int,
    leads: int,
    contact: int,
    response: int,
    meeting: int,
    opportunity: int,
    manual_leads: int,
) -> tuple[FunnelStep, ...]:
    event_note = None
    lead_note = None
    if manual_leads > 0:
        lead_note = f"Includes {manual_leads} manual lead(s) without event link."
        event_note = "Manual leads are not counted at the event step."
    return (
        FunnelStep("event", "Events discovered", events, event_note),
        FunnelStep("lead", "Leads created", leads, lead_note),
        FunnelStep("contact", "Contact outcomes", contact, None),
        FunnelStep("response", "Response outcomes", response, None),
        FunnelStep("meeting", "Meeting outcomes", meeting, None),
        FunnelStep("opportunity", "Opportunity outcomes", opportunity, None),
    )
