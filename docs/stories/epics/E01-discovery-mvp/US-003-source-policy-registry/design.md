# Design

## Domain Model

The story should formalize a `Source` or `Connector` governance model with
organization scope and these business concerns:

- Connector identity: name, domain, connector type, and authentication mode.
- Operability: enabled state, policy validity, approval status, and last known
  governance state.
- Policy inputs: allowed access mode, quota or crawl budget, time window,
  retention scope, and approved automation scope.
- Secret references: the presence and storage reference of credentials without
  exposing raw values.

Business rules:

- A source is runnable only when it is enabled, approved, within policy window,
  and within configured budget.
- Official API or feed variants outrank browser automation when both are valid
  for the same discovery need.
- Secret presence may affect readiness, but secrets remain hidden outside secure
  storage boundaries.
- Denied reasons must be explainable so later discovery jobs can fail safely.

## Application Flow

Commands:

- Create source record.
- Update source governance fields.
- Approve or disable source.
- Store or rotate connector secret reference.

Queries:

- List connector registry records for admin views.
- Get connector detail with redacted secret state.
- Evaluate runnable or denied status for a candidate source selection.

Handlers should keep policy evaluation inside backend application logic, not in
the UI and not inside browser adapters.

## Interface Contract

User-facing and admin contracts should cover:

- `GET /admin/connectors` for connector registry views.
- Minimal create or update admin routes if needed for registry management.
- Response fields that expose policy state, approval metadata, and denied
  reasons without leaking secret values.
- Consistent status semantics for enabled, disabled, denied, pending approval,
  or over-budget sources.

Errors should distinguish validation failures, secret-handling failures, and
policy-denied conditions.

## Data Model

Expected persistence work:

- Extend source or connector storage for status, connector type, domain,
  authentication mode, policy payload, approval metadata, and secret reference
  metadata.
- Keep secret material outside plain-text application records when possible
  within the MVP baseline; if local encryption is used, store only ciphertext or
  reference material in the database.
- Add indexes that support organization-scoped admin listing and domain or
  status filtering.
- Preserve retention and redaction rules for future audit and connector-history
  concerns.

## UI / Platform Impact

- Add or evolve an admin connector registry surface in the React app.
- Keep discovery-facing UI actions visibly blocked when a source is not runnable.
- Do not imply browser execution readiness just because a source record exists.
- Maintain separation between registry management and future browser-session
  tooling.

## Observability

- Record policy-denied decisions in logs and audit-friendly events without
  secret leakage.
- Surface enough structured fields to diagnose why a connector is not runnable.
- Prepare metrics hooks for denied versus runnable counts without requiring full
  dashboard work in this story.

## Alternatives Considered

1. Defer source governance and let connectors be configured ad hoc inside
   discovery jobs. Rejected because later discovery stories need a durable
   policy gate first.
2. Store raw secrets directly in the SQLite record. Rejected because it breaks
   the product contract and security rules already defined in `SPEC.md`.
