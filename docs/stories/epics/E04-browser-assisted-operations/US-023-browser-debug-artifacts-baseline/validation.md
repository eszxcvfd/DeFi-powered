# Validation

## Proof Strategy

This story is done only when LiveLead can capture governed browser debug
artifacts for supervised sessions, expose their availability through durable
metadata, enforce retention and access boundaries, and avoid storing secrets in
plaintext while keeping screenshot and debug flows usable.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Artifact type classification, debug-enabled gating, redaction or unsafe-payload blocking, retention-window calculation, and access-scope rules. |
| Integration | Manual screenshot capture, console-log or trace metadata persistence, authorized retrieval, expired artifact handling, and failed-capture safety. |
| E2E | User opens a governed session, enables or uses debug capture, takes a screenshot, sees artifact availability, and is blocked from unauthorized or expired access. |
| Platform | Story verify command keeps browser-session artifact APIs, retention handling, and session-console debug controls wired into the Harness matrix. |
| Performance | Artifact capture and retrieval stay responsive under local proof conditions and retention cleanup does not leave broken metadata or orphaned blobs. |
| Logs/Audit | Debug enablement, artifact capture, artifact access, expiry, and deletion remain diagnosable with actor, session, artifact type, policy result, and terminal status. |

## Fixtures

- Seeded governed browser session with artifact capture allowed by source and
  workspace policy.
- Browser-worker fixture that emits deterministic screenshot, console-log, and
  trace outputs.
- Unsafe payload fixture to prove redaction or blocked persistence behavior.
- Expired artifact fixture and unauthorized cross-tenant access fixture for
  negative-path proof.

## Commands

```text
- ./scripts/verify-us-023.sh — planned story verification chain for browser debug-artifact coverage
- frontend/e2e/browser-debug-artifacts.spec.ts — planned browser proof for screenshot and artifact-visibility flows
```

## Acceptance Evidence

- `tests/unit/test_browser_debug_artifacts.py` — debug gating, redaction, retention, and access rules
- `tests/integration/test_browser_debug_artifacts_api.py` — capture, metadata, retrieval, and expiry handling
- Browser session UI with debug state, screenshot control, and artifact availability feedback
- `scripts/bin/harness-cli story verify US-023` — passes with `./scripts/verify-us-023.sh`
