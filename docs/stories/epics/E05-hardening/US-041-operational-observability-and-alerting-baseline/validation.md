# Validation

## Required Proof

| Layer | Expectation |
| --- | --- |
| Unit | Rule validation rejects unknown metric, operator, severity, and channel combinations with `ALERT_RULE_INVALID`. The sanitizer strips keys, cookies, raw PII, browser storage state, and full connection strings from any payload before it is persisted. The evaluator's cooldown and deduplication logic produces exactly one `firing` row per `deduplication_key` inside the window and transitions to `resolved` when the signal clears. |
| Integration | `GET /admin/observability/summary` aggregates the `LaunchGateReport`, recent `AlertEvent` rows, backup age, worker heartbeat, and per-connector health against an in-memory SQLite + a stubbed notification dispatcher. The summary never returns secrets, raw PII, or sensitive browser state even when the underlying signal is poisoned. Rule management endpoints enforce owner/admin and reject changes to system rules. Acknowledge and resolve flows emit `alert.acknowledged` and `alert.resolved` audit entries with sanitized payloads. |
| E2E | An authenticated owner can open the new operator panel, see the summary, create a user rule that fires on a simulated signal, see the alert land in the in-app inbox from `US-029`, and acknowledge it from the panel. A simulated stale backup, missing heartbeat, connector failure spike, `NEEDS_USER_ACTION` storm, and browser crash loop each produce the documented `AlertEvent` row, severity, channel, and sanitized payload. |
| Security | Direct API calls to the new endpoints with viewer, analyst, sales, and reviewer sessions are rejected with the same error envelope as the existing admin surfaces. Sanitizer tests prove that payloads carrying API keys, cookies, raw PII, browser storage state, and full connection strings are rejected or redacted before persistence. The migration does not weaken the existing audit retention guarantee. |
| Operational | A runbook entry for the observability panel documents what an operator does when a `critical` alert fires, including the read-only nature of the evaluator and the need to act through the existing admin surfaces. The verification script proves that the seed rule set covers stale backup, missing heartbeat, connector failure spike, `NEEDS_USER_ACTION` storm, browser crash loop, and audit retention risk. |
| Platform | The `scripts/verify-us-041.sh` command wires the unit, integration, E2E, security, and operational checks together and is the same command run by `story verify` and `story verify-all`. The seed rule migration is exercised by the verify script so a missing seed rule fails the platform check, not just the data check. |

## Suggested Checks

- Backend unit tests for:
  - Rule validation against the closed enumerations.
  - Payload sanitizer against secrets, cookies, raw PII, browser
    storage state, and full connection strings.
  - Evaluator cooldown, deduplication, and resolve transitions.
  - Seed rule activation through the migration.
- Backend integration tests for:
  - `GET /admin/observability/summary`
  - Rule CRUD endpoints
  - `GET /admin/alert-events` filter and pagination
  - `POST /admin/alert-events/{id}/acknowledge`
  - Reuse of the in-app inbox and email channels from `US-029`
- E2E tests for:
  - Operator panel renders summary, rules, and recent alerts.
  - A simulated seed signal fires and the alert appears in the inbox.
  - Acknowledge action transitions the event to `acknowledged`.
- Security tests for:
  - Role enforcement on every new endpoint.
  - Payload sanitization for every new write path.
- Operational checks for:
  - Seed rule list matches the documented set in `design.md`.
  - The runbook entry exists and references the right surfaces.
  - The verify script exercises each seed signal.

## Evidence Hooks

- `tests/unit/test_alert_rules.py` — rule validation, sanitizer, evaluator
- `tests/unit/test_alert_sanitizer.py` — payload sanitization matrix
- `tests/integration/test_observability_summary_api.py`
- `tests/integration/test_alert_rules_api.py`
- `tests/integration/test_alert_events_api.py`
- `tests/integration/test_alert_acknowledgement_audit.py`
- `tests/security/test_observability_role_gates.py`
- `frontend/e2e/observability-panel.spec.ts`
- `frontend/e2e/alert-inbox-handoff.spec.ts`
- `scripts/verify-us-041.sh`
- `docs/ops/observability-runbook.md` (operational entry)
- `docs/product/observability-and-alerting.md` (living product contract)
- `docs/decisions/0019-observability-and-alerting-baseline.md` (durable
  decision record)

## Open Questions

- Should the seed rules be the same for every organization, or should
  the seed defaults be derived from the existing scoring weights and
  connector mix of the first pilot? This slice ships one fixed seed
  set; per-tenant tuning is a follow-on story.
- Should `audit.retention_breach_risk` compare against 90 days
  (`NFR-SEC-008`) or against the organization-configured retention
  floor? The first implementation follows `NFR-SEC-008` and ignores
  per-tenant overrides until a follow-on story adds the floor.
- Should the evaluator be invoked from the worker queue, the API
  process, or both? This slice uses a single worker tick plus targeted
  calls from key product paths; a follow-on story may move heavy
  evaluation to a dedicated scheduler.
- Should `POST /admin/alert-events/{id}/acknowledge` allow batch
  acknowledgement? The first implementation is single-event only.
- Should a future story wire a Prometheus exporter or an OTel collector
  behind the existing sanitization helper? This slice does not commit
  to that direction; it only preserves a stable seam.
