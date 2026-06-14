# Browser Debug Artifacts And Retention

Source: `SPEC.md` sections 5.10, 7.2, 7.3, 8.10, 11, 14.2, and `UC-04`.

## Product Goal

Sales, analyst, and admin users need a governed way to capture browser-session
debug artifacts when supervised automation needs investigation or proof.
LiveLead must define when screenshot, console-log, and trace artifacts may be
captured, how users access them, how long they are retained, and how the
system prevents secrets or cross-tenant data leakage while keeping browser
debugging practical.

## MVP Scope

This product slice covers:

- Opt-in debug capture for supervised browser sessions and supported browser
  actions.
- Manual screenshot capture from the browser session console when the current
  session policy allows local artifact capture.
- Automatic console-log and trace capture only when debugging is enabled for
  the session.
- Durable metadata for captured artifacts, including artifact type, session,
  actor or system trigger, timestamps, storage reference, and retention expiry.
- Access control and retention enforcement for browser debug artifacts.

This product slice does not yet cover:

- Browser profile create, lock, expire, or delete workflows.
- CloakBrowser approval workflow or compliance review.
- Full video recording, HAR archives, or broad browser forensic packages.
- Permanent storage of cookies, storage state, or plaintext secrets as
  downloadable artifacts.
- Scheduled export or delivery of browser debug artifacts outside the product.

## Contract Rules

- Browser debug artifacts may be captured only for a governed browser session
  and only when current source policy, workspace policy, and role permissions
  allow the requested capture mode.
- Manual screenshot capture counts as a local artifact and should be available
  only when the session is active or in a recent terminal state where the
  worker still has a valid artifact context.
- Console logs and browser traces must be captured only when debugging is
  enabled explicitly for that session or action scope.
- Artifact metadata must remain durable and queryable even when the artifact
  blob is stored outside SQLite.
- Artifact payloads must not expose plaintext credentials, cookies, raw storage
  state, or other secrets; the system should redact or block unsafe payloads
  before persistence.
- Access to artifacts must remain tenant-scoped, role-gated, and auditable.
- Artifact retention must honor the configured expiry window; expired artifacts
  should no longer be downloadable, and their durable metadata should reflect
  expiration or deletion status.
- Debug capture must stay supplemental to supervised workflow; enabling debug
  must not widen action permissions or bypass confirmation rules for side-
  effect actions.

## API Surface

- Session creation or session-debug configuration should expose whether debug
  capture is enabled for that session.
- Browser session status should expose whether artifacts are available and the
  latest artifact summary without embedding large blobs in the status payload.
- The browser-session surface should support manual screenshot requests for an
  eligible active session.
- Artifact reads should return metadata and governed download or view access for
  authorized users only.

## UI Surface

The MVP artifact slice should deepen the browser session console:

- Visible debug-enabled state for the current session.
- Manual "Take screenshot" control when allowed.
- Artifact panel or list that shows screenshot, console-log, and trace
  availability with timestamps and status.
- Clear empty, expired, unauthorized, and capture-failed states.

## Validation Implications

- Unit proof should cover retention calculation, artifact classification,
  redaction or blocking of unsafe payloads, and access-scope rules.
- Integration proof should cover metadata persistence, artifact-store writes,
  download authorization, retention expiry handling, and failed-capture safety.
- E2E proof should cover enabling debug, taking a screenshot, viewing artifact
  availability, and respecting unauthorized or expired states in the UI.
- Logs or audit proof should confirm who enabled debug, requested captures,
  accessed artifacts, and when artifacts expired or were deleted.
- Platform proof should keep the future browser-artifact verification command
  wired into the Harness matrix before profile-management or CloakBrowser
  policy stories build on it.
