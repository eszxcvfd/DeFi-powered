# Campaign And ICP

Source: `SPEC.md` sections 5.2, 7.2, 12, 14.1, and UI-002.

## Product Goal

Analysts need to define a reusable campaign target before discovery starts. The
campaign contract must capture market intent, ICP filters, keyword criteria,
business positioning, target-market focus, and initial scoring-weight
preferences in a way that later discovery, scoring, and lead workflows can
consume without re-entering the same context.

## MVP Scope

This product slice covers:

- Creating, listing, viewing, and updating campaigns.
- Accepting either a structured campaign form or a natural-language GenAI brief
  that becomes editable campaign criteria.
- Capturing campaign intent: name, description, target industry, product or
  service focus, market regions, languages, timezone, date range, positive
  keywords, exclude keywords, and business model framing.
- Capturing ICP criteria: industry, organization type, company size, role or
  title targets, country or region, pain points, use cases, positive keywords,
  and excluded keywords.
- Capturing target-market weighting or regional focus as part of campaign
  strategy.
- Capturing scoring-weight configuration as editable campaign settings, even
  before downstream event scoring is implemented.
- Rendering a user-facing campaign setup flow that makes later source and
  discovery dependencies visible without pretending they already work.

This product slice does not yet cover:

- Source registry or source approval.
- Running discovery jobs.
- Event scoring execution or re-score workflows.
- Campaign cloning.
- Industry templates for Charity/Nonprofit, Tokenization/RWA, or Cross-border
  Payment.

## Contract Rules

- Campaign records are organization-scoped.
- Users must be able to save campaign and ICP data before any source is chosen.
- When a user starts with a natural-language brief, the product must preserve
  both the original brief and the editable structured criteria derived from it.
- The API and UI must expose target industry and product or service focus as
  explicit user inputs, even if the first persistence cut stores them inside a
  typed criteria payload rather than first-class columns.
- The campaign contract must support business-model framing and target-market
  weighting as first-class inputs, not hidden notes.
- The campaign detail contract must return both ICP criteria and scoring-weight
  settings together so later discovery and scoring stories can snapshot them.
- If the system infers assumptions while parsing a brief, those assumptions
  must remain reviewable and editable by the user.
- Source selection and discovery-run actions may appear in the UI only as
  clearly deferred or disabled surfaces until the corresponding stories land.
- Editing campaign criteria after creation is allowed; downstream effects on
  discovery snapshots and re-scoring are deferred to later stories.

## API Surface

- `GET /campaigns`: return campaign summaries for the current organization.
- `POST /campaigns`: create a campaign with market intent, ICP criteria, and
  scoring-weight settings.
- `POST /campaigns/briefs:parse`: convert a natural-language brief into
  editable campaign criteria and target-market suggestions.
- `GET /campaigns/{id}`: return full campaign detail including ICP and scoring
  weights.
- `PATCH /campaigns/{id}`: update editable campaign fields without requiring a
  discovery job.

## UI Surface

The MVP campaign surface should introduce the `UI-002` wizard shape without
claiming more behavior than the backend supports:

- Step 1: objective and campaign identity.
- Step 2: natural-language brief or industry, product or service focus, and
  keyword criteria.
- Step 3: ICP criteria and audience hypothesis inputs.
- Step 4: market region, language, timezone, date window, and target-market
  weighting.
- Step 5: source selection shown as planned or disabled until `US-003`.
- Step 6: scoring weights, guardrails, and business positioning editable and
  reviewable.
- Step 7: review and save available; run-discovery CTA disabled until `US-004`.

The app should also provide a minimal campaign list or index surface so users
can return to existing campaigns after the first save.

## Validation Implications

- Unit proof should cover campaign payload validation, brief parsing contracts,
  and ICP field mapping.
- Integration proof should cover persistence, organization scoping, and API
  request or response shapes.
- E2E proof should cover creating a campaign through the UI and reopening it in
  the list or detail flow.
- Platform proof should confirm frontend and backend story verification commands
  remain wired into the Harness matrix.
