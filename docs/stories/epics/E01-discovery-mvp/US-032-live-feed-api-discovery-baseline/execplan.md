# Exec Plan

## Goal

Define and implement the first real external discovery slice so LiveLead can
run governed live `API`/`RSS`/`ICS` connectors from manual discovery jobs and
turn the returned items into canonical event review data without jumping
straight to browser automation.

## Scope

In scope:

- Approved live feed/API connector execution in manual discovery jobs.
- Policy-aware runnable or denied source selection for live sources.
- Canonical event ingestion from live feed/API output.
- Per-source progress, counts, partial success, and safe blocked states.
- Secret-safe connector readiness or failure context in admin and job views.

Out of scope:

- Playwright website connectors.
- Selenium or alternate browser-adapter connectors.
- Interactive login, browser session launch, or delegated-auth workflows.
- Scheduled sync, incremental cursors, or long-running polling.
- Full connector-health dashboards.

## Risk Classification

Risk flags:

- External systems.
- Data model.
- Audit/security.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- External provider behavior.
- Audit/security.
- Removing or weakening validation requirements.

## Work Phases

1. Discovery: confirm live-source requirements from `SPEC.md`, existing
   discovery contracts, and source-governance rules.
2. Design: define feed/API connector metadata, source-readiness semantics,
   provenance needs, and safe-stop behavior.
3. Validation planning: design proof for stubbed live sources, policy deny,
   partial success, canonical event ingestion, and secret-safe diagnostics.
4. Implementation: extend source metadata, discovery runners, normalization
   flow, and UI/job-status projections for live-source execution.
5. Verification: prove live-source discovery produces reviewable canonical
   events without bypassing policy or leaking secrets.
6. Harness update: keep product docs current, update durable story status, and
   leave a clean handoff for Playwright and Selenium follow-on stories.

## Stop Conditions

Pause for human confirmation if:

- Product behavior is ambiguous.
- Data migration or deletion risk appears.
- Validation requirements need to be weakened.
- Architecture direction changes.
- The first live-source slice cannot stay inside official feed/API access and
  would require browser automation or delegated-auth platform APIs instead.
- The team wants scheduled sync, connector analytics, or browser fallback folded
  into this baseline.
