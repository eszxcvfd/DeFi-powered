# Exec Plan

## Goal

Define and implement the first governed discovery-copilot slice so LiveLead can
answer natural-language discovery questions with structured, grounded, and
reviewable recommendations that feed into query expansion or discovery prep.

## Scope

In scope:

- Campaign-scoped natural-language discovery questions.
- Structured copilot response with claims, evidence, confidence, assumptions,
  risk flags, query framing, and recommended source scope.
- Explicit user-controlled handoff from copilot recommendations into query
  expansion or discovery prep.
- Grounding and uncertainty rules for the first copilot slice.

Out of scope:

- Autonomous discovery execution.
- Generic open-domain chat.
- Outreach/content generation workflows.
- Long-lived multi-turn autonomous memory.
- Feedback/learning analytics.

## Risk Classification

Risk flags:

- External systems.
- Audit/security.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- External provider behavior.
- Removing or weakening validation requirements.

## Work Phases

1. Discovery: confirm discovery-copilot requirements from `SPEC.md`,
   query-expansion contracts, and AI output rules.
2. Design: define structured response schema, grounding boundaries, acceptance
   linkage, and uncertainty/risk signaling.
3. Validation planning: design proof for schema enforcement, grounded answers,
   acceptance handoff, and no-autonomous-execution behavior.
4. Implementation: add bounded copilot API/UI flow, provider validation, and
   linkage into query expansion/discovery prep.
5. Verification: prove copilot answers remain structured, reviewable, and do
   not bypass human control.
6. Harness update: keep product docs current, update durable story status, and
   leave a clean handoff for later feedback or memory stories.

## Stop Conditions

Pause for human confirmation if:

- Product behavior is ambiguous.
- Data migration or deletion risk appears.
- Validation requirements need to be weakened.
- Architecture direction changes.
- The story would require autonomous execution or generic assistant behavior
  instead of bounded discovery planning.
