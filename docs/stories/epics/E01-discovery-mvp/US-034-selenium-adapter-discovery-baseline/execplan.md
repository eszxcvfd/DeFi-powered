# Exec Plan

## Goal

Define and implement the first governed `Selenium`/alternate-adapter discovery
slice so LiveLead can run bounded extraction recipes through a non-`Playwright`
browser adapter and turn the results into canonical event review records without
breaking the shared discovery contract.

## Scope

In scope:

- Approved `Selenium`/alternate-adapter connector execution in manual discovery
  jobs.
- Source-scoped engine selection and readiness validation.
- Canonical event ingestion from alternate-adapter extraction output.
- Per-source progress, engine family, partial success, and challenge-safe
  blocked states.
- Secret-safe engine readiness or failure context in admin and job views.

Out of scope:

- Interactive login, saved-state reuse, or private/member-only site support.
- Manual browser-session UX and explicit action controls.
- Confirmation-gated actions or external-side-effect actions.
- Optional-engine governance expansion.
- Full connector-health dashboards or distributed grid admin workflows.

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

1. Discovery: confirm `Selenium`/alternate-adapter requirements from `SPEC.md`,
   discovery contracts, and automation boundary rules.
2. Design: define engine-selection metadata, adapter eligibility, extraction
   provenance, and challenge/timeout safe-stop behavior.
3. Validation planning: design proof for fixture-site alternate-adapter
   discovery, policy deny, blocked challenge states, canonical event ingestion,
   and common-interface adapter cleanup.
4. Implementation: extend connector metadata, discovery orchestration,
   browser-worker runner, extraction mapping, and UI/job-status projections for
   alternate-adapter execution.
5. Verification: prove alternate-adapter discovery produces reviewable
   canonical events without bypassing policy or hard-coding browser SDK choices
   into business logic.
6. Harness update: keep product docs current, update durable story status, and
   leave a clean handoff for later runtime/governance expansion.

## Stop Conditions

Pause for human confirmation if:

- Product behavior is ambiguous.
- Data migration or deletion risk appears.
- Validation requirements need to be weakened.
- Architecture direction changes.
- The first alternate-adapter slice cannot stay read-only and bounded and would
  require login, saved-state reuse, or confirmation-gated actions instead.
- The team wants optional-engine governance or distributed grid operations
  folded into this baseline.
