# Platform And Automation Policy

Source: `SPEC.md` sections 2.5, 3.4, 3.5, 5.3, 5.10, and 11, plus
`docs/product/mvp-scope-and-priorities.md`.

Related durable decisions:

- `docs/decisions/0010-livelead-sqlite-primary-store.md`
- `docs/decisions/0011-livelead-technology-baseline.md`

## Runtime Direction

US-001 provides smoke entrypoints for all listed processes except object-storage
(deferred). See `docs/FOUNDATION_RUNTIME.md`.

MVP should use a modular monolith with separate processes only where operational
isolation is needed:

- `web-api`: Python API surface.
- `worker`: discovery and AI jobs.
- `scheduler`: scheduled discovery and synchronization.
- `browser-worker`: isolated browser automation runtime.
- `frontend`: interactive web UI.
- `sqlite-db`: business data in a project-local SQLite file such as
  `data/livelead.sqlite3`.
- `redis`: queue, cache, rate limits, and locks.
- `object-storage`: screenshots, HTML snapshots, exports, and artifacts.

## Technology Baseline

- Backend: Python 3.12+, FastAPI, Pydantic.
- Database: project-local SQLite with SQLAlchemy 2.x and Alembic.
- Queue: Redis-backed Dramatiq.
- Browser automation: Playwright Python by default, Selenium as a fallback
  adapter, optional CloakBrowser only after compliance review.
- Frontend: React with TypeScript on Vite.
- UI components: shadcn/ui.
- AI: OpenAI-compatible provider abstraction, with local providers allowed only
  behind the same interface.
- Testing: Pytest, Playwright E2E, and targeted Hypothesis coverage.
- Observability: OpenTelemetry instrumentation, Sentry for errors, and
  Prometheus/Grafana for metrics and dashboards.
- Packaging: Docker Compose for development and single-host MVP packaging.

## Automation Rules

- Business logic must not import Playwright, Selenium, or CloakBrowser directly.
- Official API, RSS, Atom, sitemap, or ICS sources are preferred over browser
  automation when suitable.
- Source policy must be checked before a job runs.
- Jobs must stop or enter `NEEDS_USER_ACTION` when CAPTCHA, MFA, or bot
  challenge behavior appears.
- Headed interactive sessions are allowed when the user must log in or supervise.
- Browser automation is a supporting access path for the core MVP jobs, used
  only when permitted feeds, official APIs, or simpler manual review paths are
  not sufficient. It must not become the primary product surface.
- Sending content, posting, destructive actions, or external communication must
  require preview and confirmation.
  The first confirmation-gated slice is defined in
  `docs/product/browser-confirmation-and-preview.md`.
- External communication should default to copy/manual handoff or one explicit
  confirmation-gated action at a time; bulk or autonomous send flows are out of
  MVP scope across all supported channels.
- Read-only browser actions may run only from an explicit connector allowlist
  with stable-locator and timeout guardrails. The first action slice is defined
  in `docs/product/browser-read-only-actions-and-guardrails.md`.
- Browser debug artifacts such as screenshots, console logs, and traces must
  stay opt-in, retention-controlled, and secret-safe. The first artifact slice
  is defined in `docs/product/browser-debug-artifacts-and-retention.md`.
- Reusable browser profiles and saved browser-state material must remain
  consent-aware, tenant-scoped, and secret-safe. The first profile lifecycle
  slice is defined in `docs/product/browser-profile-lifecycle-and-consent.md`.
- CloakBrowser must remain optional, source-scoped, approval-gated, and
  kill-switchable. The first CloakBrowser governance slice is defined in
  `docs/product/cloakbrowser-policy-and-approvals.md`.
- Credentials and secrets must not be stored as plaintext or written to logs.
- The SQLite database file must stay inside the project directory and outside
  version control.

## Validation Implications

Automation and platform stories need proof beyond unit tests:

- Integration proof for source policy enforcement, job state transitions, secret
  redaction, and adapter contracts.
- E2E proof for user-visible discovery, approval, and browser-session flows.
- Logs/audit proof for sensitive actions and generated-content approval.
- Security proof for tenant isolation, RBAC, secret handling, and privacy rules.
