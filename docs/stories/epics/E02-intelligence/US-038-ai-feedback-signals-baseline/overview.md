# Overview

## Current Behavior

LiveLead already returns reviewable audience hypotheses and structured discovery
copilot recommendations, but users still cannot record whether those AI-assisted
outputs were actually helpful, wrong, or uncertain. `SPEC.md` explicitly asks
for user feedback on AI output and audience hypotheses, and later scoring
stories reserve room for learning from that signal, yet there is no governed
feedback contract or story packet for the first slice.

## Target Behavior

This story should establish the first AI-feedback slice for analysis outputs:

- Let users give governed feedback on discovery-copilot responses.
- Let users mark audience hypotheses as correct, incorrect, or uncertain.
- Preserve structured reason codes and optional notes with actor attribution.
- Reflect the latest effective feedback state in the relevant review surfaces.
- Keep feedback available for later reviewed improvement workflows without
  auto-changing prompts, weights, or ranking behavior.

This story should add a bounded human-feedback layer without widening into
autonomous learning, generalized assistant memory, or content-approval
replacement.

## Affected Users

- Analysts who want to mark whether discovery guidance or audience analysis was
  actually useful.
- Sales/BD users who need better review continuity before acting on AI-assisted
  recommendations.
- Owners/Admins who need feedback capture to stay tenant-scoped, explainable,
  and non-autonomous.
- Future implementation agents extending scoring-adjustment suggestions, AI
  quality review, or memory workflows.

## Affected Product Docs

- `docs/product/ai-feedback-and-learning-signals.md`
- `docs/product/discovery-copilot-and-structured-briefing.md`
- `docs/product/audience-hypotheses-and-evidence.md`
- `docs/product/event-scoring-and-priority.md`

## Non-Goals

- Automatic prompt, provider, or scoring-weight updates from feedback alone.
- Generic assistant memory or cross-campaign personalization.
- Replacing approval states already used for generated content.
- Workspace-wide feedback analytics dashboards.
- Browser-assisted external execution driven by feedback.
