# Exec Plan

## Goal

Define and implement the minimum generated-content slice that turns engagement
plans into editable draft variants with preserved metadata and visible safety
flags.

## Scope

In scope:

- Draft generation from event and plan context.
- Content settings for type, platform, language, tone, length, market, and CTA.
- Context preview before generation.
- Variant persistence, inline editing, and risk flags.
- Proof that drafts stay separate from approval and sending workflows.

Out of scope:

- Approval workflow and approval history.
- Copy/export and “used” lifecycle transitions.
- Automatic or browser-assisted sending.
- Prompt-learning loops.
- Lead or pipeline actions.

## Risk Classification

Risk flags:

- Audit/security.
- External systems.
- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- External provider behavior because generation depends on an AI-provider
  boundary.
- Audit/security because content safety and sensitive-targeting guardrails are
  part of the contract.

## Work Phases

1. Discovery: confirm generation, metadata, and safety requirements from
   `SPEC.md`, product docs, and current engagement-plan behavior.
2. Design: define draft persistence, provider boundary, risk flags, and safe
   lifecycle boundaries without dragging in approval or export workflows.
3. Validation planning: design proof for draft generation, metadata
   preservation, risk flags, and inline editing.
4. Implementation: add generation flow, draft storage, content UI, and safety
   signaling.
5. Verification: prove deterministic or provider-backed draft generation and
   edit flow end to end.
6. Harness update: record story proof, keep product docs current, and leave a
   clean handoff for approval stories.

## Stop Conditions

Pause for human confirmation if:

- The story starts requiring approval workflow to feel useful.
- Provider behavior forces hidden prompt or policy decisions that need a durable
  decision record.
- Validation would need to weaken spam, evidence, or sensitive-targeting
  guardrails.
- The content surface starts depending on export, browser execution, or lead
  workflows to feel complete.
