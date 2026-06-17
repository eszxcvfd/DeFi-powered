# Pilot Live Rollback Runbook (US-040)

Source: `docs/decisions/0018-pilot-live-cutover-baseline.md`,
`docs/ops/pilot-live-cutover-runbook.md`.

Use this runbook when the team needs to roll the pilot-live
environment back to `test_like` or `paused` after a serious issue,
or to recover from a botched cutover drill.

## When to Roll Back

- A live connector or AI provider is producing data that violates
  retention, lawful basis, or rate-limit policy.
- An operator notices silent failures in the live environment that
  the launch gate did not catch.
- A restore rehearsal reveals data loss or corruption.
- The team needs to take a real-environment break for an
  architectural change and cannot leave `pilot_live` running.

## Decide the Target Mode

- `test_like`: the most defensive rollback. The system returns to
  the dev-friendly defaults (dev headers are still disabled because
  the env config keeps that flag off, but no live integrations are
  enabled). Use this when you do not yet know what went wrong.
- `paused`: useful when you want to keep the launch-gate history
  active but stop all live activity. Use this when the team plans
  to resume the pilot after investigation.

## Execute the Rollback

```bash
curl -sk \
  -H 'Cookie: livelead_session=…' \
  -H 'Content-Type: application/json' \
  -d '{"reason":"AI provider incident; pausing pilot", "target_mode":"paused"}' \
  https://api.example.com/admin/cutover/rollback
```

The endpoint:

- Sets the environment to the chosen target mode.
- Disables every live integration toggle.
- Records a `cutover_events` row with `action=rollback` and the
  operator's reason.
- Emits an audit entry with `action=environment.rolled_back`.

## After the Rollback

- Confirm the rollback via `GET /admin/runtime-readiness` and
  `GET /admin/live-toggles`. All toggles must report `disabled`.
- Inspect `GET /admin/cutover/events` to confirm the rollback row
  was written and to read the recorded gate snapshot.
- Rehearse the restore flow against the most recent backup:

  ```bash
  cp data/livelead.sqlite3 data/livelead.sqlite3.bak
  sqlite3 data/livelead.sqlite3 < last_backup.sql
  curl -sk -H 'Cookie: livelead_session=…' \
    -d '{"status":"verified_restore"}' \
    -H 'Content-Type: application/json' \
    https://api.example.com/admin/backup-snapshots/<backup_id>:verify
  ```

- Decide whether to enter `pilot_live` again or stay in
  `test_like`/`paused` until a follow-on story lands. Either
  decision must be recorded in the audit log via the
  `enter-pilot-live` or `pause` endpoints.
- Add a friction note via
  `scripts/bin/harness-cli intervention --kind review --summary …` so
  the next pilot cutover can avoid the same failure.

## Out of Scope

- Restoring from a backup is **not** part of the rollback endpoint.
  The endpoint freezes activity and clears live toggles; data
  restoration is a separate, operator-driven flow that uses the
  backup metadata recorded by `POST /admin/backup-snapshots:record`.
- Cross-region failover, blue/green, or zero-downtime orchestration
  are out of scope for this slice.
