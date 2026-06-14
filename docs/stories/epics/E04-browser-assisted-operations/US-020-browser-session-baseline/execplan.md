# Exec Plan

## Goal

Define and implement the first supervised browser-session slice that lets users
open an isolated browser session from a supported event or source, observe live
status in the UI, and stop the session safely before richer browser actions or
profile-management stories arrive.

## Scope

In scope:

- Browser session launch from supported event or source entrypoints.
- Isolated session context or governed profile boundary selection.
- Session status reads with engine, state, URL, runtime, and latest-action
  summary.
- Safe stop or close flow for queued or running sessions.
- Baseline lifecycle events needed for UI status updates.

Out of scope:

- Allowlisted action execution beyond session startup or stop.
- Destructive-action confirmation flows.
- Screenshot, console-log, or trace retention.
- Browser profile create, lock, expire, or delete workflows.
- CloakBrowser approval or browser-send automation.

## Risk Classification

Risk flags:

- External systems.
- Public contracts.
- Cross-platform.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- External provider behavior via browser automation keeps this story high-risk,
  even though the first slice stays bounded to supervised session lifecycle.

## Work Phases

1. Discovery: confirm browser-session requirements from `SPEC.md`, `UC-04`,
   automation policy, and current event/source contracts.
2. Design: define the session lifecycle, isolation semantics, stop behavior, and
   reportable live-status fields.
3. Validation planning: design proof for policy gating, lifecycle transitions,
   UI status visibility, and safe cleanup.
4. Implementation: add the browser-session backend flow, worker coordination,
   and first browser console UI.
5. Verification: prove users can launch, observe, and stop governed sessions.
6. Harness update: leave a clean handoff for action-execution, confirmation, and
   artifact stories.

## Stop Conditions

Pause for human confirmation if:

- The story needs destructive browser actions or outbound posting to satisfy the
  baseline.
- Session isolation requires a new cross-tenant credential or secret model.
- Validation requirements need to weaken around policy enforcement, stop safety,
  or audit visibility.
- The implementation needs a different architecture shape than the current
  isolated `browser-worker` baseline.
