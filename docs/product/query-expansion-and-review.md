# Query Expansion And Review

Source: `SPEC.md` sections 5.2, 5.4, 7.2, 11, 12, 14.1, and `UI-002`.

## Product Goal

Analysts need discovery to search with richer keyword coverage than the raw
campaign criteria alone, while still staying reviewable and controlled. The
product contract should define the first governed query-expansion slice that
can generate keyword variants across synonyms, abbreviations, languages, and
industry phrasing, require human review when AI contributes expansions, and
snapshot the approved variant set into discovery execution.

## MVP Scope

This product slice covers:

- Generating candidate discovery-query variants from campaign criteria.
- Supporting bounded expansion categories such as synonyms, abbreviations,
  alternate language phrasing, and industry-specific terminology.
- Keeping expansion suggestions grouped and explainable rather than returning an
  opaque keyword blob.
- Requiring user review and edit before run when AI-generated expansion is used.
- Reusing approved expansion sets across manual discovery runs and scheduled
  discovery templates.
- Preserving enough expansion provenance to explain which approved query set was
  used for a discovery job.

This product slice does not yet cover:

- Conversational discovery copilot question/answer workflows. That first slice
  is defined in
  `docs/product/discovery-copilot-and-structured-briefing.md`.
- Autonomous AI query regeneration during a running job.
- Fully automated expansion approval with no user review path.
- Broad multilingual translation management or glossary administration.
- Performance analytics or effectiveness scoring for expansion strategies.

## Contract Rules

- Query expansion must begin from campaign-scoped criteria; it cannot create a
  free-floating discovery intent outside a campaign or approved brief context.
- Expansion suggestions must stay structured by variant type such as synonym,
  abbreviation, language, or industry phrase.
- If AI contributes any expansion suggestions, the user must be able to review,
  remove, edit, or accept them before launch; they must not be silently applied
  to a first run.
- The approved expansion set used for a discovery job must be snapshotted so job
  review can explain which variants were active.
- Manual runs and scheduled runs may reuse a saved approved expansion set, but
  later edits should affect only future runs.
- Expansion results must preserve assumptions or risk markers when a suggestion
  is inferred rather than directly user-provided.
- Query expansion must not bypass source policy, campaign scope, or discovery
  review controls.
- Empty or low-confidence expansion is valid; the system must prefer a smaller
  trustworthy set over fabricated breadth.

## API Surface

- `POST /campaigns/{id}/query-expansions:generate` or equivalent route:
  generate candidate keyword/query variants from current campaign criteria.
- `GET /campaigns/{id}/query-expansions` or equivalent route: return the latest
  saved or approved expansion set.
- `PATCH /campaigns/{id}/query-expansions` or equivalent route: update approved
  variants, remove suggestions, or accept edited expansion output.
- Discovery-job create and scheduled-discovery flows should reference the
  approved expansion snapshot used for execution rather than inventing a second
  query API at run time.
- Discovery copilot accept (`POST .../discovery-copilot:accept`) may create a
  pending_review expansion set from proposed query framing; same approval rules
  apply before `use_expansion` on job create.

## UI Surface

- Campaign discovery surfaces can request candidate query expansion from current
  criteria before launch.
- Users can review grouped variants, edit/remove unwanted suggestions, and
  explicitly approve the final expansion set.
- Manual discovery launch and schedule setup can show whether they will use raw
  campaign criteria or an approved expanded query set.
- The first UX should stay operator-focused and reviewable rather than acting
  like an autonomous chat assistant.

## Validation Implications

- Unit proof should cover variant grouping, approval requirements, snapshot
  rules, and empty/low-confidence handling.
- Integration proof should cover expansion persistence, campaign scoping,
  approved-set reuse for manual/scheduled runs, and explainable snapshot linkage
  to discovery jobs.
- E2E proof should cover generating suggestions, editing/approving them, and
  launching discovery with the approved expansion set.
- Logs and audit proof should confirm who generated, edited, approved, or
  replaced an expansion set and which snapshot was used for a later run.
- Platform proof should keep expansion verification wired into the Harness
  matrix before discovery-copilot Q&A stories widen the AI surface.

## Implementation status

- **US-036 implemented:** generate / patch / approve, snapshot on discovery jobs
  and scheduled dispatch, campaign UI.
- **Proof:** `./scripts/verify-us-036.sh`, `frontend/e2e/query-expansion.spec.ts`,
  `scripts/bin/harness-cli story verify US-036`.
