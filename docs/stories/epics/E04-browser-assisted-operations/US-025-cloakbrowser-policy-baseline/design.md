# Design

## Domain Model

The story should formalize the first CloakBrowser governance objects:

- `CloakBrowserApproval`: source-scoped approval aggregate with owner/admin
  approval, compliance approval, rationale, timestamps, and terminal state.
- `CloakBrowserPolicyState`: bounded state such as disabled, requested, pending,
  approved, revoked, blocked, or runtime-failed.
- `CloakBrowserRuntimePolicy`: pinned-version, checksum or signature evidence,
  upgrade policy, and kill-switch configuration for the optional engine.
- `CloakBrowserBlockedReason`: explicit reason mapping for unapproved, revoked,
  disabled, runtime-check-failed, or policy-denied states.
- `CloakBrowserUsageScope`: source, tenant, and intended-purpose metadata that
  prevents approval from leaking into unrelated workflows.

Business rules:

- CloakBrowser must remain optional and disabled by default.
- Approval requires both Owner/Admin authorization and compliance approval.
- Approval is source-scoped and purpose-scoped; it does not generalize across
  all connectors or tenants.
- Kill-switch state must override previously approved status immediately.
- Runtime policy failures such as unpinned version or checksum mismatch must
  block CloakBrowser use even when the source was previously approved.
- CloakBrowser approval must never imply permission to bypass source terms,
  authentication challenges, or unauthorized access controls.

## Application Flow

- `RequestCloakBrowserEnablement` records that a source is asking for the
  optional engine and captures rationale and scope.
- `ApproveCloakBrowserForSource` records Owner/Admin and compliance approval
  once all prerequisites are present.
- `RevokeCloakBrowserApproval` removes approval or marks it revoked when policy
  changes, a source review fails, or a kill-switch event occurs.
- `EvaluateCloakBrowserRuntimePolicy` checks pinned version, checksum or
  signature evidence, and environment kill-switch status before runtime
  selection.
- `ResolveBrowserEngineForSource` chooses Playwright, Selenium, or denies
  CloakBrowser based on policy state and runtime checks.
- Admin read flows return approval state, runtime-policy status, and blocked
  reasons without exposing sensitive binary or environment secrets.

## Interface Contract

Backend contract should minimally support:

- Admin policy routes to request, approve, revoke, or inspect CloakBrowser
  enablement for a source.
- Connector or source detail responses that include CloakBrowser approval and
  blocked-state metadata.
- Runtime or session-selection outcomes that distinguish pending approval,
  revoked, checksum-failed, disabled-engine, and approved states.
- Kill-switch actions or equivalent config surfaces that can disable
  CloakBrowser quickly and explain the resulting blocked state.

Expected payload concerns:

- Approval responses should expose roles, timestamps, rationale summary, and
  scope without leaking secrets.
- Runtime-policy status should be explainable without exposing raw binary
  contents or privileged deployment details.
- The contract should preserve current engine-agnostic business logic by
  confining CloakBrowser specifics to policy and adapter boundaries.

## Data Model

- Store CloakBrowser approval metadata in SQLite with source, tenant, approval
  actors, timestamps, rationale, runtime-policy status, and terminal state.
- Persist kill-switch and runtime-policy references as governed configuration or
  metadata, not as ad hoc business-logic flags.
- Keep enough metadata to explain historical approvals, revocations, and
  runtime-check failures through audit and admin surfaces.
- Preserve room for future packaging or deployment decisions without redefining
  the source-scoped approval model.

## UI / Platform Impact

- Extend connector or source governance UI with CloakBrowser request, approval,
  revoke, and blocked-state visibility.
- Show pinned-version, checksum or signature status, and kill-switch feedback in
  an operator-friendly way.
- Make approved and blocked engine states readable without implying that the
  optional engine changes allowed browser actions.
- Keep CloakBrowser governance inside admin or operator surfaces rather than
  normal analyst session flows.

## Observability

- Record audit and diagnostics for request, approval, revoke, runtime-policy
  failure, kill-switch activation, and attempted CloakBrowser use.
- Keep structured blocked reasons and engine-selection outcomes queryable.
- Preserve enough linkage to connect source policy, approval actors, runtime
  policy, and browser-session engine selection.

## Alternatives Considered

1. Treat CloakBrowser as just another engine toggle with no extra governance.
   Rejected because the SPEC requires explicit approval, provenance review, and
   kill-switch controls.
2. Roll CloakBrowser policy directly into source registry without a dedicated
   bounded slice. Rejected because approval, runtime policy, and revoke behavior
   have enough risk to deserve their own story contract.
3. Make CloakBrowser the default when available. Rejected because the current
   architecture and policy docs keep Playwright as the default and CloakBrowser
   behind explicit gates.
