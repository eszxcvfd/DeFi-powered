# Exec Plan

## Goal

Define and implement the minimum manual discovery lifecycle that lets LiveLead
create, run, stream, and cancel deterministic discovery jobs safely before any
live external connector work starts.

## Scope

In scope:

- Manual discovery launch from a valid campaign.
- Snapshotting campaign criteria and selected source context into the job.
- Queue or worker lifecycle for deterministic mock connectors.
- Job states, per-source progress, terminal outcomes, and cancellation behavior.
- Source-policy checks before a mock run starts.
- User-visible progress transport and API status contract.
- Controlled retry semantics for transient failures.

Out of scope:

- Live API, RSS, Playwright, or Selenium discovery runs.
- Full event-ranking and detail-review UX.
- Scheduled discovery.
- AI query expansion.
- Interactive login or browser-session flows.

## Risk Classification

Risk flags:

- Public contracts.
- Existing behavior.
- Audit/security.
- Weak proof.
- Multi-domain.

Hard gates:

- Audit/security.
- Removing or weakening validation requirements.

## Work Phases

1. Discovery: confirm job lifecycle, streaming events, cancel rules, retry
   rules, and mock-connector scope from `SPEC.md` and current product docs.
2. Design: define discovery job entities, state transitions, mock connector
   contract, and UI/API boundaries without coupling to live browser tooling.
3. Validation planning: design proof for worker orchestration, streaming, policy
   deny, cancellation, and partial-success outcomes.
4. Implementation: add job persistence, worker flow, deterministic mock
   connectors, progress transport, and frontend run/progress surfaces.
5. Verification: prove lifecycle transitions, policy gates, retries, terminal
   outcomes, and resource cleanup.
6. Harness update: record evidence, update matrix proof, and leave clear
   handoff assumptions for live connector stories.

## Stop Conditions

Pause for human confirmation if:

- The story needs live external connectors to make meaningful progress.
- Progress streaming requires a fundamentally different transport choice than
  the MVP app can support without an architectural change.
- Validation for cancellation, policy deny, or partial-success outcomes would
  need to be weakened.
- Job lifecycle work starts forcing domain logic to import browser or framework
  details directly.
