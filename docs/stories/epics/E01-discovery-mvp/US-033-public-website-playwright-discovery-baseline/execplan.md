# Exec Plan

## Goal

Define and implement the first governed public-website discovery slice so
LiveLead can run `Playwright` browser recipes inside manual discovery jobs and
turn extracted website data into canonical event review records without
crossing into manual browser-console or destructive-action workflows.

## Scope

In scope:

- Approved public-website `Playwright` connector execution in manual discovery
  jobs.
- Bounded browser recipe metadata and readiness validation.
- Canonical event ingestion from website extraction output.
- Per-source progress, counts, partial success, and challenge-safe blocked
  states.
- Secret-safe website connector readiness or failure context in admin and job
  views.

Out of scope:

- Selenium or alternate adapter discovery.
- Interactive login, saved-state reuse, or private/member-only site support.
- Manual browser-session UX and explicit action controls.
- Confirmation-gated actions or external-side-effect actions.
- Full recipe-builder UI and connector-health dashboards.

## Risk Classification

Risk flags:

- External systems.
- Audit/security.
- Public contracts.
- Existing behavior.
- Cross-platform.
- Multi-domain.

Hard gates:

- External provider behavior.
- Audit/security.
- Removing or weakening validation requirements.

## Work Phases

1. Discovery: confirm `Playwright` recipe requirements from `SPEC.md`,
   discovery contracts, and browser-governance contracts.
2. Design: define recipe metadata, readiness semantics, extraction provenance,
   and challenge/timeout safe-stop behavior.
3. Validation planning: design proof for fixture-site discovery, policy deny,
   blocked challenge states, canonical event ingestion, and clean adapter
   lifecycle.
4. Implementation: extend connector metadata, discovery orchestration,
   browser-worker runner, extraction mapping, and UI/job-status projections for
   website-source execution.
5. Verification: prove website discovery produces reviewable canonical events
   without bypassing policy or widening into uncontrolled browser automation.
6. Harness update: keep product docs current, update durable story status, and
   leave a clean handoff for Selenium discovery.

## Stop Conditions

Pause for human confirmation if:

- Product behavior is ambiguous.
- Data migration or deletion risk appears.
- Validation requirements need to be weakened.
- Architecture direction changes.
- The first website-discovery slice cannot stay read-only and bounded and would
  require login, saved-state reuse, or confirmation-gated actions instead.
- The team wants Selenium or full browser-console behavior folded into this
  baseline.
