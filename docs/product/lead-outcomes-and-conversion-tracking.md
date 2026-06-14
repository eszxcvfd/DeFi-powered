# Lead Outcomes And Conversion Tracking

Source: `SPEC.md` sections 4.4, 5.11, 5.12, 8, `AC-BIZ-09`, and the open KPI
question in section 17.

## Product Goal

Sales and analyst users need the lead workflow to continue past stage movement
into explicit conversion outcomes that can be reviewed, explained, and later
reported. The product contract must define how LiveLead lets users record manual
contact, response, meeting, and opportunity outcomes on a lead, preserve them in
the activity timeline, optionally link them to content already used, and create
durable reporting truth before funnel, content-effectiveness, or CRM-sync
stories arrive.

## MVP Scope

This product slice covers:

- Manually recording a lead outcome when contact, response, meeting, or
  opportunity milestones happen.
- Storing actor, timestamp, notes, and optional linked content context for each
  outcome entry.
- Showing outcome history in the lead timeline and latest-outcome summary in
  lead detail or pipeline surfaces when appropriate.
- Applying baseline validation so outcome records do not contradict clearly
  incompatible lead states.
- Preserving enough structured data for later funnel and content-effectiveness
  reports.

This product slice does not yet cover:

- CRM synchronization or automatic outcome import.
- Funnel aggregation or reporting visualization. The first funnel slice is
  defined in `docs/product/funnel-reporting-and-conversion-steps.md`.
- Content-effectiveness comparisons or attribution dashboards. The first
  attribution slice is defined in
  `docs/product/content-effectiveness-and-attribution.md`.
- Browser-assisted sending or automatic outcome detection from external systems.
- Revenue modeling, deal stages beyond opportunity, or closed-won forecasting.

## Contract Rules

- Outcome entries must be append-only timeline facts rather than overwriting
  past lead history.
- Every outcome entry must stay linked to one lead and preserve actor and
  occurrence time.
- The first manual outcome slice should cover the funnel-relevant milestones
  needed later for reporting: contact, response, meeting, and opportunity.
- Linking an outcome to used content is optional, but when present it must refer
  to durable content history rather than free-form guessed attribution.
- Outcome recording must not imply autonomous outreach, CRM sync, or external
  messaging already happened unless the user explicitly records that fact.
- Invalid contradictions, such as opportunity outcomes on obviously disallowed
  lead states, should be blocked or surfaced clearly.

## API Surface

- Lead detail and list payloads should expose latest-outcome summary when one
  exists.
- Outcome-create action or equivalent endpoint should accept outcome type,
  occurred-at time, notes, and optional linked content id.
- Outcome history query should return timeline-ready entries with actor and lead
  context.

## UI Surface

The MVP outcome slice should deepen the lead workspace before funnel reporting:

- Manual record-outcome action from lead detail or equivalent lead workspace.
- Outcome entries visible in lead timeline.
- Latest-outcome cue in lead detail and pipeline views when useful.
- Clear distinction between stage movement and recorded outcome facts.

## Validation Implications

- Unit proof should cover allowed outcome types, contradiction guards,
  content-link validation, and timeline-entry creation.
- Integration proof should cover outcome persistence, latest-outcome read
  models, and API validation for invalid combinations or missing lead context.
- E2E proof should cover recording an outcome on a lead, seeing it appear in the
  timeline, and optionally linking it to previously used content.
- Logs or audit proof should confirm who recorded which outcome, when, and with
  what linked content or notes.
- Platform proof should keep the future outcome verification command wired into
  the Harness matrix before funnel or content-effectiveness stories build on it.
