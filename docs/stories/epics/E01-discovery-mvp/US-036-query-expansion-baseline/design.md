# Design

## Domain Model

The story should formalize the first governed query-expansion objects:

- `QueryExpansionSet`: campaign-scoped collection of candidate or approved query
  variants with generation mode, status, and versioning.
- `QueryExpansionVariant`: one structured variant with text, variant type,
  source mode, confidence/assumption markers, and user-edited state.
- `QueryExpansionSnapshot`: immutable expansion selection linked to a discovery
  job or scheduled-discovery template for later review.

Business rules:

- Expansion originates from existing campaign criteria and cannot redefine the
  campaign objective independently.
- AI-generated variants require explicit human review before first-run use.
- User-provided or user-edited variants may be approved directly once validation
  passes.
- Expansion sets may evolve over time, but historical job snapshots stay
  immutable.
- Empty approved expansion is acceptable; discovery may still run on raw
  campaign criteria when the user rejects all suggestions.

## Application Flow

- `GenerateQueryExpansion` reads current campaign criteria and returns grouped
  candidate variants with provenance and assumption markers.
- `ApproveQueryExpansionSet` validates the edited selection and marks a set
  usable for future manual/scheduled discovery.
- `GetApprovedQueryExpansion` returns the currently approved set for campaign
  detail or discovery launch surfaces.
- `SnapshotQueryExpansionForRun` links the approved set or explicit raw-criteria
  choice into discovery-job creation and scheduled-dispatch templates.
- `ReplaceQueryExpansionSet` preserves history when a campaign owner regenerates
  or substantially revises the approved expansion.

## Interface Contract

This baseline should extend campaign/discovery prep surfaces rather than create
an AI-chat API:

- `POST /campaigns/{id}/query-expansions:generate` generates candidate variants.
- `GET /campaigns/{id}/query-expansions` returns current approved/candidate
  state.
- `PATCH /campaigns/{id}/query-expansions` saves edits and approval state.
- Discovery-job and schedule routes continue to own run creation, but they
  should expose which expansion snapshot they used.

Expected payload concerns:

- Responses should group variants by type and clearly separate user-originated
  terms from AI-generated suggestions.
- AI-derived variants should carry assumptions/risk markers without pretending
  unsupported certainty.
- Run/schedule payloads should indicate whether execution used raw criteria or
  an approved expansion snapshot.

## Data Model

- Add durable campaign-scoped storage for expansion sets, variants, approval
  status, and version history.
- Preserve immutable expansion snapshots linked to discovery jobs and schedule
  templates.
- Reuse existing campaign/discovery ownership boundaries instead of creating a
  global search-term registry.
- Add query support needed for latest approved set reads and historical snapshot
  lookups.

## UI / Platform Impact

- Campaign detail/discovery prep UI should offer expansion generation and review
  before manual run or schedule save.
- Variant review UI should support grouped browsing, inline edit/remove, and
  explicit approve/save actions.
- Manual run and scheduled discovery forms should show whether an approved
  expansion snapshot will be used.
- Platform work stays inside existing campaign/discovery plus AI/provider
  boundaries; this story is not yet a free-form chat surface.

## Observability

- Record structured diagnostics for generation mode, approval transitions,
  snapshot linkage, and rejected/empty outcomes.
- Keep audit outputs explainable with actor, campaign id, expansion-set id,
  approval state, and downstream run linkage.
- Preserve enough counters/metrics to support later effectiveness analysis
  without requiring that dashboard in this baseline.

## Alternatives Considered

1. Jump directly to discovery copilot Q&A before a structured expansion layer
   exists. Rejected because copilot needs a governed artifact to produce and
   reuse.
2. Auto-apply AI expansion silently to discovery runs. Rejected because
   `SPEC.md` explicitly requires user review when AI is involved.
3. Keep expansion as ephemeral per-run UI state only. Rejected because
   scheduled runs and later job review need durable snapshots.
