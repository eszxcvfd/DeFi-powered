# Event Scoring And Priority

Source: `SPEC.md` sections 5.6, 5.8, 7.2, 12, `UI-003`, `UI-004`, `UC-01`, and `UC-02`.

## Product Goal

Analysts and sales users need canonical events to become prioritized work, not
just reviewable records. The product contract must define how LiveLead
calculates a campaign-aware event score, derives priority levels, persists a
versioned scoring result, and explains why an event was ranked the way it was
before engagement-plan or lead workflows arrive.

## MVP Scope

This product slice covers:

- Calculating an event score from 0 to 100 for canonical events within a
  campaign context.
- Applying campaign scoring weights that were captured in `US-002`.
- Deriving a configurable priority level from workspace threshold rules.
- Persisting a versioned score snapshot with weight metadata and calculation
  time.
- Showing score badges or equivalent summary signals in event results.
- Showing an explainable score breakdown in event detail, including evidence,
  missing data, and score-reducing factors.
- Supporting an explicit re-score action when campaign weights or event data
  change.

This product slice does not yet cover:

- Full audience-hypothesis generation workflows.
- AI-generated engagement plans or content creation.
- Bulk re-score actions across many events.
- Automatic learning that changes scoring weights without approval.
- Lead conversion, outreach, or browser-assisted actions.

## Contract Rules

- Score calculation is campaign-aware. The same canonical event may score
  differently for different campaigns because campaign weights or fit criteria
  differ.
- Total score must stay within `[0,100]`, and priority level must be derived
  from the active threshold configuration rather than hard-coded UI labels.
- Every score exposed to users must keep `scoring_version`, the effective
  weights snapshot, `calculated_at`, and enough component detail to explain the
  result later.
- Score explanations must separate observed evidence, derived component values,
  missing data, and low-confidence inputs instead of overstating certainty.
- Re-score must create an audit-friendly new scoring result or equivalent
  versioned update without mutating canonical event facts as if they were newly
  observed source data.
- The first scoring slice may use deterministic heuristics for components that
  do not yet have their own dedicated product slices, but it must not invent
  unsupported audience claims or sensitive inferences.
- Audience-related or accessibility-related components may use source-visible
  event cues before a fuller audience story lands, but those cues must stay
  explainable and visibly limited.

## API Surface

- `GET /campaigns/{id}/events`: list canonical events with score summary,
  priority level, and missing-score state when a score has not been computed.
- `GET /events/{id}`: return latest score summary, score breakdown,
  `scoring_version`, component evidence, and missing-data explanations.
- `POST /events/{id}/rescore`: request a score recalculation using the current
  campaign weights and current canonical event data.

## UI Surface

The MVP scoring slice should extend the event review surfaces introduced by
`US-005`:

- Event results table with score badge and priority state.
- Event detail score surface with component breakdown and explanation.
- Clear missing-score or stale-score states when re-score is needed.
- Deferred or placeholder audience, engagement, and lead actions when those
  stories have not landed yet.

## Validation Implications

- Unit proof should cover score math, threshold mapping, rounding or clamping,
  and explanation assembly.
- Integration proof should cover score persistence, version metadata, list and
  detail API behavior, and explicit re-score behavior.
- E2E proof should cover reviewing ranked events and opening a score breakdown
  from the UI.
- Logs or audit proof should confirm recalculation and score-version changes
  stay explainable without leaking secrets or pretending unsupported evidence.
- Platform proof should keep the scoring verification path wired into the
  Harness matrix for later audience, engagement, and lead stories.
