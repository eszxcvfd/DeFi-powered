# Design

## Domain Model

The story should formalize the first browser debug-artifact objects:

- `BrowserDebugArtifact`: durable metadata record for one artifact captured from
  a supervised session.
- `BrowserArtifactType`: bounded artifact kind such as `screenshot`,
  `console_log`, or `trace`.
- `BrowserArtifactCaptureMode`: whether capture is manual, automatic-on-debug,
  or system-triggered by a failure path.
- `BrowserArtifactAccessScope`: tenant, role, and session linkage used to prove
  who may view or download the artifact.
- `BrowserArtifactRetention`: retention window, expiry timestamp, and terminal
  status such as active, expired, deleted, or blocked.

Business rules:

- Artifact capture must remain scoped to one governed browser session.
- Manual screenshots are allowed only when policy allows local artifacts and
  the session is eligible for capture.
- Console-log and trace capture require explicit debug enablement for the
  session or action scope.
- Secrets, cookies, raw storage state, and unsafe payloads must be redacted,
  blocked, or excluded before persistence.
- Artifact access must remain tenant-scoped, role-gated, and auditable.

## Application Flow

- `EnableBrowserSessionDebug` sets or confirms debug capture for a session
  using current policy and permission checks.
- `CaptureBrowserScreenshot` requests a governed manual screenshot from the
  browser worker and stores durable artifact metadata.
- `FinalizeBrowserDebugArtifacts` persists console-log and trace references for
  the session when debug capture is enabled and the worker has emitted them.
- `ListBrowserSessionArtifacts` returns artifact metadata for the session
  without embedding large blobs.
- `GetBrowserArtifactAccess` authorizes view or download access for one
  artifact and rejects expired, cross-tenant, or unauthorized requests.
- A retention job or equivalent expiry path should mark artifacts expired and
  remove or hide underlying blobs according to current retention policy.

## Interface Contract

Backend contract should minimally support:

- Session status fields or a related session-artifact query that exposes
  whether debug mode is enabled and which artifacts are available.
- Manual screenshot request flow from the browser session console.
- Artifact metadata read or list flow that returns type, capture time, status,
  expiry, and authorized access information.
- Error states for unauthorized access, expired artifacts, disabled debug
  capture, and failed capture writes.

Expected payload concerns:

- Artifact responses should favor metadata and governed links or download
  tokens, not inline large payload blobs.
- Console-log payloads should be sanitized to avoid secret leakage.
- The contract should leave room for future profile-lifecycle and advanced
  forensic artifacts without redefining the core artifact model.

## Data Model

- Store browser debug-artifact metadata in SQLite with references to session,
  user, source or event context, artifact type, capture mode, storage path or
  object key, status, and expiry timestamps.
- Keep artifact blobs outside SQLite, consistent with the current storage
  baseline for large artifacts.
- Persist enough metadata to support audit, retention cleanup, and authorized
  retrieval without needing worker-memory-only state.
- Retention rules should support artifact-specific expiry windows and preserve a
  durable record that the artifact once existed even after blob deletion.

## UI / Platform Impact

- Extend the browser session console with debug-enabled status, a manual
  screenshot control, and an artifact availability panel.
- Show empty, capture-in-progress, available, expired, unauthorized, and
  failed-capture states clearly.
- Keep artifact controls visually distinct from browser actions so debug capture
  does not look like unrestricted automation.
- Preserve the current session console as the main surface rather than creating
  a separate artifact-management console for this first slice.

## Observability

- Record audit and diagnostics for debug enabled or disabled, manual screenshot
  requests, automatic artifact capture, artifact access, expiry, deletion, and
  blocked unsafe payloads.
- Keep metrics or structured counters for artifact volume, capture failures,
  retention cleanup outcomes, and unauthorized access attempts.
- Preserve enough linkage to correlate API request, browser session, worker
  capture, artifact metadata, and retention outcome.

## Alternatives Considered

1. Store screenshot, console-log, and trace blobs directly in SQLite. Rejected
   because the current baseline keeps large artifacts outside the primary
   database.
2. Capture all artifacts by default for every browser session. Rejected because
   it expands privacy and storage risk without a clear MVP need.
3. Delay manual screenshot until profile-management exists. Rejected because the
   session console already exposes "Take screenshot" in the SPEC and users need
   immediate debugging value before profile administration.
