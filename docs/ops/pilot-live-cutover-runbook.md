# Pilot Live Cutover Runbook (US-040)

Source: `docs/decisions/0018-pilot-live-cutover-baseline.md`,
`docs/product/real-environment-cutover-and-live-operations.md`,
`SPEC.md` (sections 2.4, 3.2, 3.3, 10, 11, 14, 15).

This runbook is the first operator-facing guide for moving LiveLead
from `test_like` to `pilot_live`. It is intentionally narrow: the
goal is a safe, single-host or small-footprint live cutover, not a
full enterprise rollout.

The runbook pairs with `scripts/verify-us-040.sh` so the launch
evidence lives next to the operator checklist.

## Pre-flight Checklist

- [ ] All US-040 unit and integration tests pass:
  `PYTHONPATH=src .venv/bin/python -m pytest tests/unit/test_runtime_*.py
  tests/integration/test_runtime_readiness_api.py`
- [ ] The repo-root `.env` is provisioned for the real environment.
  Required keys: `LIVELEAD_ENVIRONMENT_MODE=test_like`,
  `LIVELEAD_AUTH_ALLOW_DEV_HEADERS=false`,
  `LIVELEAD_AUTH_COOKIE_SECURE=true`,
  `LIVELEAD_SECRET_MASTER_KEY=<Fernet key, NOT the dev placeholder>`,
  `LIVELEAD_LAUNCH_GATE_BACKUP_MAX_AGE_HOURS=26`,
  `LIVELEAD_LAUNCH_GATE_WORKER_HEARTBEAT_MAX_SECONDS=300`,
  `LIVELEAD_LAUNCH_GATE_MIN_BACKUP_COUNT=1`,
  `LIVELEAD_PILOT_LIVE_ADMIN_PIN=<shared secret>`.
- [ ] API, worker, scheduler, and browser-worker processes are running
  behind TLS (TLS terminated upstream; `LIVELEAD_AUTH_COOKIE_SECURE=true`).
- [ ] Daily backup script writes the SQLite file to
  `data/livelead.sqlite3` and records the snapshot via
  `POST /admin/backup-snapshots:record`.
- [ ] Owner and admin accounts are seeded (`ensure_default_owner` runs
  on first API boot).
- [ ] Audit log and connector surfaces are reachable.

## Step 1 — Verify Readiness Read-Only

```bash
curl -sk -H 'Cookie: livelead_session=…' https://api.example.com/admin/runtime-readiness
```

Confirm:

- `mode` is `test_like` while the operator verifies.
- `gate.passed` is `true` after the team has disabled dev headers,
  rotated secrets, recorded at least one backup, and confirmed the
  worker heartbeat is recent.
- `toggles[*].state` is `disabled` for all four live integrations.
- `backup_freshness` is `fresh`.

If any blocking check is reported, fix it before continuing. The
`blocking[]` list in the response points to the exact cause.

## Step 2 — Promote to `pilot_live`

```bash
curl -sk \
  -H 'Cookie: livelead_session=…' \
  -H 'Content-Type: application/json' \
  -d '{"reason":"first pilot go-live", "admin_pin":"<shared secret>"}' \
  https://api.example.com/admin/cutover/enter-pilot-live
```

The endpoint returns:

- `event`: a `cutover_events` row that records the transition.
- `previous_mode` and `new_mode` — confirm `pilot_live`.
- `gate`: the full launch-gate snapshot at the moment of entry.

The cutover is rejected (HTTP 409) if:

- the launch gate is not passing,
- there are fewer than `LIVELEAD_LAUNCH_GATE_MIN_BACKUP_COUNT`
  recorded/verified backup snapshots, or
- the `LIVELEAD_PILOT_LIVE_ADMIN_PIN` does not match.

All rejections are also recorded in the audit log with
`outcome=denied` so an operator can see why the cutover was blocked.

## Step 3 — Enable Live Integrations

Enable each integration with an explicit `approval_note`. The note is
recorded in the audit log so the change is traceable to a reason and
an approver.

```bash
curl -sk \
  -H 'Cookie: livelead_session=…' \
  -H 'Content-Type: application/json' \
  -d '{"approval_note":"approved by owner for pilot go-live"}' \
  https://api.example.com/admin/live-toggles/discovery:enable

curl -sk \
  -H 'Cookie: livelead_session=…' \
  -H 'Content-Type: application/json' \
  -d '{"approval_note":"Gemini key provisioned and tested"}' \
  https://api.example.com/admin/live-toggles/ai_copilot:enable

curl -sk \
  -H 'Cookie: livelead_session=…' \
  -H 'Content-Type: application/json' \
  -d '{"approval_note":"SMTP secrets configured; delivery tested"}' \
  https://api.example.com/admin/live-toggles/notifications:enable

curl -sk \
  -H 'Cookie: livelead_session=…' \
  -H 'Content-Type: application/json' \
  -d '{"approval_note":"supervised browser access approved"}' \
  https://api.example.com/admin/live-toggles/browser_external:enable
```

The list endpoint reports the current toggle state:

```bash
curl -sk -H 'Cookie: livelead_session=…' \
  https://api.example.com/admin/live-toggles
```

## Step 4 — Post-Cutover Smoke / UAT

Confirm the operator checklist:

- [ ] `GET /health/live` returns `ok`.
- [ ] `GET /health/ready` returns `ok` with no blocking checks.
- [ ] An authenticated owner signs in to the workspace.
- [ ] A campaign is created or loaded and persisted.
- [ ] A discovery job is created and runs against an approved
  connector.
- [ ] At least one canonical event is reviewed and scored.
- [ ] An AI-assisted generation path (copilot or content) runs
  end-to-end with the live provider.
- [ ] A supervised browser session is launched against a governed
  source and the action list shows the expected allowlisted actions.
- [ ] A notification (in-app or email) is delivered end-to-end for
  one of the test cases above.

If any smoke step fails, follow `pilot-live-pause-runbook.md`
immediately.

## Step 5 — Daily Operational Loop

- Confirm `GET /admin/runtime-readiness` shows `backup_freshness=fresh`
  and the worker heartbeat is recent.
- Review the audit log for `environment.*` and `environment.toggle.*`
  entries; investigate any unexpected transitions.
- Re-run `scripts/verify-us-040.sh` after every release to keep the
  US-040 evidence current.

## Out of Scope

- Multi-region deployment, blue/green, zero-downtime orchestration.
- Kubernetes migration or distributed microservice control plane.
- Automatic horizontal autoscaling.
- Cost optimization.
- Broad performance tuning beyond the first live guardrails.

For those, open a follow-on story and update this runbook.
