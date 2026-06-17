# Pilot Live Pause Runbook (US-040)

Source: `docs/decisions/0018-pilot-live-cutover-baseline.md`,
`docs/ops/pilot-live-cutover-runbook.md`.

Use this runbook when an operator needs to halt new risky activity
quickly without deleting data or breaking safe read-only visibility.

## When to Pause

- A live connector starts returning errors that the team cannot
  diagnose within the SLA.
- The AI provider hits a rate limit or an unexpected content
  moderation flag.
- The browser-worker shows recurring crashes or a CAPTCHA detection
  signal.
- Notifications deliver spam or fail repeatedly.
- The launch gate begins failing and the team needs time to
  investigate without losing data.

## Pause the Environment

```bash
curl -sk \
  -H 'Cookie: livelead_session=…' \
  -H 'Content-Type: application/json' \
  -d '{"reason":"notification provider returning 5xx for 10 minutes"}' \
  https://api.example.com/admin/cutover/pause
```

The endpoint:

- Sets the environment to `paused`.
- Disables every currently-enabled live integration toggle.
- Records a `cutover_events` row with `action=pause` and the
  operator's reason.
- Emits an audit entry with `action=environment.paused` and the
  same reason.

## Verify the Pause

```bash
curl -sk -H 'Cookie: livelead_session=…' \
  https://api.example.com/admin/live-toggles
```

All four toggles should report `state=disabled`.

```bash
curl -sk -H 'Cookie: livelead_session=…' \
  https://api.example.com/admin/runtime-readiness
```

`mode` should be `paused`.

## Re-enable Live Operations

Re-enable integrations one at a time, exactly as described in
`pilot-live-cutover-runbook.md` step 3. Each enable requires a
fresh `approval_note` and the launch gate must pass.

If the environment needs to be returned to `test_like` instead of
`pilot_live`, see `pilot-live-rollback-runbook.md`.
