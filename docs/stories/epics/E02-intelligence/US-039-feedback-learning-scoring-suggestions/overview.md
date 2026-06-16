# Overview

## Current Behavior

LiveLead now has campaign scoring, audience hypotheses, discovery copilot, and
governed AI feedback signals, but the feedback stops at observation. `SPEC.md`
allows the system to suggest scoring-weight changes from feedback as long as it
does not auto-apply them, yet there is no product contract or story packet for
that first feedback-learning workflow.

## Target Behavior

This story should establish the first governed scoring-suggestion slice:

- Turn campaign-scoped feedback signals into reviewable scoring-weight
  suggestions.
- Explain which feedback patterns drove each proposed change.
- Show current versus proposed scoring weights before any change is applied.
- Require explicit approval or rejection for each suggestion set.
- Preserve suggestion history and approval outcomes for audit and later review.

This story should add a bounded feedback-learning workflow without widening into
autonomous ranking optimization, generic AI memory, or black-box retraining.

## Affected Users

- Owners/Admins who govern campaign scoring and need safe review of suggested
  changes.
- Analysts who want ranking improvements informed by accumulated feedback but
  still under human control.
- Future implementation agents extending adaptive ranking, AI quality review, or
  broader model-personalization workflows.

## Affected Product Docs

- `docs/product/feedback-learning-and-scoring-suggestions.md`
- `docs/product/ai-feedback-and-learning-signals.md`
- `docs/product/event-scoring-and-priority.md`
- `docs/product/campaign-and-icp.md`

## Non-Goals

- Automatic scoring-weight changes with no approval.
- Cross-tenant or global learning across organizations.
- Broad analytics dashboards for every AI feedback surface.
- Prompt-template mutation or provider switching from feedback alone.
- Generic memory or personalization features unrelated to campaign scoring.
