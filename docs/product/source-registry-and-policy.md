# Source Registry And Policy

Source: `SPEC.md` sections 5.3, 7.2, 11, 12, 14.1, and 14.2.

## Product Goal

Admins and analysts need a governed source catalog before any connector can run.
The product must make it clear which sources are allowed, how they should be
accessed, what limits apply, and which operational safeguards can stop a run
before data collection crosses policy boundaries.

## MVP Scope

This product slice covers:

- A registry of configured sources or connectors with connector type, domain,
  status, access policy, rate-limit settings, authentication mode, and approval
  metadata.
- Channel families relevant to the product scope, including website event
  pages, webinar platforms, YouTube, LinkedIn, Facebook, X, Instagram, TikTok,
  Pinterest, Threads, Discord, forums, blogs, and community sites.
- Policy-aware selection rules that prefer official API, RSS, Atom, sitemap, or
  ICS sources before browser automation when both are viable.
- Policy enforcement inputs needed before discovery execution, including enabled
  state, quota or budget limits, allowed time window, and policy validity.
- Secret-handling expectations for API keys, cookies, and credentials.
- Admin-facing visibility into connector readiness and policy state through an
  initial `/admin/connectors` management surface.
- Connector health aggregation. The first connector health surface is defined
  in `docs/product/connector-health-surface.md`; the bounded surface extends the
  source catalog with a per-connector health snapshot, a recent-errors rollup,
  and a closed `ConnectorHealthStatus` enum.
- Connector policy metadata that later browser-session stories can use to decide
  which read-only actions are allowlisted.

This product slice does not yet cover:

- Live discovery execution against external sources beyond the first feed or
  API slice defined in `docs/product/live-feed-and-api-discovery.md`.
- Full browser recipe authoring UX.
- Interactive login sessions. The first supervised browser-session slice is
  defined in `docs/product/browser-session-console-and-isolation.md`.
- Governed browser-profile lifecycle and consented saved-state reuse. That
  first profile slice is defined in
  `docs/product/browser-profile-lifecycle-and-consent.md`.
- CloakBrowser approval and source-scoped optional-engine policy. That first
  CloakBrowser slice is defined in
  `docs/product/cloakbrowser-policy-and-approvals.md`.
- Read-only browser action execution. That first allowlisted action slice is
  defined in `docs/product/browser-read-only-actions-and-guardrails.md`.
- CAPTCHA handling workflows beyond deny or safe-stop requirements.
- Connector health analytics dashboards.

## Contract Rules

- Source records are organization-scoped governance objects even when the same
  external platform can appear in more than one tenant.
- The registry should preserve enough metadata to distinguish platform family,
  connector type, and communication surface because later engagement flows are
  multi-channel.
- A connector cannot be treated as runnable unless it is enabled, approved, and
  has a valid source policy record.
- Source policy must expose enough information for later orchestrator checks:
  access mode, allowed time window, quota or budget, retention expectations,
  and approval metadata.
- When an official API or feed source is suitable, the product contract must
  preserve that preference rather than defaulting to browser automation.
- Feed or API connector records must preserve enough endpoint, parser, and
  stable-identity metadata for the first live external discovery slice to run
  without pushing provider logic into business rules.
- Browser-discovery connector records must preserve enough recipe, engine, and
  bounded-readiness metadata for a `Playwright` discovery slice to run without
  turning the registry into an unrestricted browser-script store.
- Alternate-adapter connector records must preserve explicit engine-selection
  and readiness metadata so `Selenium` or another approved adapter can run
  through the same discovery contract without hard-coding engine choice into
  business logic.
- Secrets must never be returned in plain form from admin query surfaces and
  must never be written to logs.
- Browser-oriented connector configuration may be stored, but this story does
  not claim that browser execution already works.
- Denied, disabled, expired, or over-quota sources must be distinguishable in
  API and admin UI state so later discovery stories can fail safely.

## API Surface

- `GET /admin/connectors`: list connector or source registry records with status,
  connector type, domain, policy state, authentication mode, and approval
  metadata.
- Admin create or update routes may be introduced in this story if needed to
  support a minimal registry workflow, but they must not bypass policy or secret
  handling rules.
- Discovery-facing internal queries must be able to load runnable-source
  decisions without exposing raw secrets.

## Admin UI Surface

The initial admin surface should focus on governance, not connector execution:

- Connector list or registry table with enabled or disabled state, connector
  type, domain, authentication mode, and approval status.
- Detail or editor surface for policy fields such as access mode, quota or
  budget, time window, and retention scope.
- Clear signals when a source is not runnable because it is disabled, lacks
  approval, exceeds quota, or has no valid policy.
- Secret presence can be indicated, but secret values must not be displayed.

## Validation Implications

- Unit proof should cover policy evaluation rules and source-state mapping.
- Integration proof should cover persistence, approval metadata, secret
  redaction, and runnable or denied policy decisions.
- E2E proof should cover an admin managing source records and seeing blocked
  states before discovery execution exists.
- Logs and audit proof should confirm denied policy decisions and secret-safe
  behavior.
- Platform proof should keep the policy-aware backend and admin UI checks wired
  into the Harness matrix.
