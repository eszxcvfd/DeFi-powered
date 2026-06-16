# Exec Plan

## Goal

Define and implement the first governed AI-feedback slice so LiveLead can record
human judgment on discovery-copilot responses and audience hypotheses without
widening into autonomous learning or generic assistant memory.

## Scope

In scope:

- Discovery-copilot response feedback.
- Audience-hypothesis correctness feedback.
- Structured reason codes and optional notes.
- Tenant-scoped persistence, effective-state projection, and auditability.
- Feedback visibility in discovery-copilot and audience-review surfaces.

Out of scope:

- Automatic scoring-weight or prompt-template changes.
- Workspace-wide quality dashboards.
- Generated-content approval replacement.
- Multi-turn autonomous memory or personalization.
- Browser-assisted execution triggered by feedback.

## Risk Classification

Risk flags:

- Audit/security.
- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- Removing or weakening validation requirements.
- Any move toward autonomous learning or cross-tenant feedback leakage.

## Work Phases

1. Discovery: confirm feedback requirements from `SPEC.md`, audience-analysis
   contracts, discovery-copilot contracts, and scoring-learning boundaries.
2. Design: define target types, state vocabularies, reason-code rules, and
   append-only versus current-state feedback behavior.
3. Validation planning: design proof for tenant scoping, update semantics,
   auditability, and no-auto-learning guardrails.
4. Implementation: add bounded feedback APIs, persistence/projection support,
   and UI controls in discovery-copilot and audience-review surfaces.
5. Verification: prove users can leave and revise feedback safely without
   mutating underlying AI artifacts or triggering autonomous changes.
6. Harness update: keep product docs current, update durable story status, and
   leave a clean handoff for later scoring-adjustment suggestions or AI-memory
   stories.

## Stop Conditions

Pause for human confirmation if:

- The story starts requiring feedback on additional AI surfaces beyond discovery
  copilot and audience hypotheses.
- Product behavior becomes ambiguous between lightweight feedback and approval
  workflow states.
- Validation would need to weaken auditability, tenant scope, or no-auto-
  learning guarantees.
- The story starts requiring generic chat history or long-lived assistant
  memory to feel complete.
