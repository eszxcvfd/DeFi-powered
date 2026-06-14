# Validation

## Proof Strategy

This story is done only when LiveLead can let users copy or export approved
content, mark it used through an explicit handoff action, and keep approved
versus used content distinguishable without implying outbound sending.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Approved-only gating, export-format validation, used-state transitions, and handoff audit metadata rules. |
| Integration | Export endpoint or flow behavior, mark-used persistence, usage-status retrieval, and invalid handoff attempts. |
| E2E | User opens approved content, copies or exports it, marks it used, and sees updated status or handoff history in the UI. |
| Platform | Story verify command keeps backend handoff behavior, export flow, and frontend content-handoff checks wired into the Harness matrix. |
| Performance | Export generation and usage-state retrieval stay responsive for local approved-content fixtures. |
| Logs/Audit | Copy, export, and mark-used actions remain diagnosable with actor, timestamp, and approved-revision context. |

## Fixtures

- One approved-content fixture ready for handoff.
- One used-content fixture showing post-handoff status.
- Export fixtures for supported formats such as Markdown and CSV.
- Negative fixtures for unapproved-content export attempts and invalid used
  transitions.

## Commands

Add commands after scripts exist.

```text
./scripts/verify-us-011.sh
```

## Acceptance Evidence

- `./scripts/verify-us-011.sh` — chains through `verify-us-010` / `verify-foundation` (full platform + e2e suite), then handoff unit/integration tests
- `harness-cli story verify US-011` — recorded after successful run
