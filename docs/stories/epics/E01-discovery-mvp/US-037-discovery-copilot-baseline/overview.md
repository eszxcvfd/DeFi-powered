# Overview

## Current Behavior

LiveLead now supports campaign setup, real discovery connectors, recurring
discovery schedules, and governed query expansion. However, analysts still need
to manually translate fuzzy discovery intent into structured search setup.
`SPEC.md` calls for a GenAI discovery copilot that can answer natural-language
questions about livestream search scope and turn them into structured guidance,
but there is no dedicated product contract or story packet for that surface.

## Target Behavior

This story should establish the first discovery-copilot slice for LiveLead:

- Accept bounded natural-language discovery questions tied to a campaign or
  explicit discovery context.
- Return a structured response with claims, evidence, confidence, assumptions,
  risk flags, proposed query framing, and recommended source scope.
- Let users carry approved recommendations into query expansion or discovery
  prep instead of executing them automatically.
- Keep copilot answers grounded, uncertainty-aware, and reviewable.
- Preserve enough provenance that later operators can understand which question
  and context produced a recommendation.

This story should add a natural-language planning surface without widening into
autonomous execution, generic chat, or content-generation workflows.

## Affected Users

- Analysts who want faster discovery planning from natural-language questions.
- Owners/Admins who need AI-assisted discovery advice to stay grounded,
  explainable, and reviewable.
- Future implementation agents extending feedback loops, multi-turn memory, or
  broader copilot surfaces on top of a structured response contract.

## Affected Product Docs

- `docs/product/query-expansion-and-review.md`
- `docs/product/discovery-copilot-and-structured-briefing.md`
- `docs/product/campaign-and-icp.md`

## Non-Goals

- Autonomous discovery execution from copilot output.
- Generic open-domain chat.
- Outreach/content generation beyond discovery planning.
- Long-lived multi-turn autonomous memory.
- AI feedback/learning analytics.
