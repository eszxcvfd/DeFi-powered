# Overview

## Current Behavior

`US-006` makes canonical events rankable through scoring, but users still do
not see a concrete audience hypothesis that explains who the event is likely to
attract or why that audience matters. The event detail surface has no dedicated
audience contract, no structured evidence-linked hypothesis records, and no
privacy guardrail specific to audience inference.

## Target Behavior

This story should establish the first audience-analysis slice after scoring:

- Generate audience hypotheses for a scored canonical event.
- Explain why each audience segment may fit the event and campaign.
- Link each hypothesis to source evidence or clearly labeled inference.
- Expose confidence-aware audience review in event detail.
- Preserve enough structured metadata for later feedback and engagement stories.

This story makes prioritization more interpretable. It does not yet claim
audience-feedback loops, engagement-plan generation, content approval, or lead
conversion workflows.

## Affected Users

- Analyst.
- Sales/BD.
- Viewer.
- Future engagement and lead-workflow implementation agents.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/event-results-and-review.md`
- `docs/product/event-scoring-and-priority.md`
- `docs/product/audience-hypotheses-and-evidence.md`

## Non-Goals

- User feedback on hypothesis correctness.
- AI-generated engagement plans or message variants.
- Private attendee discovery or profile enrichment.
- Bulk compare, bulk outreach, or lead conversion actions.
- Browser-assisted actions from the audience surface.
