# Validation

## Proof Strategy

This story is done only when LiveLead can generate bounded query-expansion
variants, require review when AI contributes suggestions, and reuse an approved
expansion snapshot safely across manual and scheduled discovery runs.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Variant grouping, approval requirements, empty/low-confidence handling, and snapshot immutability rules. |
| Integration | Expansion persistence, campaign scoping, approved-set reuse for manual/scheduled runs, and run/schedule linkage to immutable expansion snapshots. |
| E2E | User generates suggestions, edits/removes variants, approves the final set, and launches discovery using the approved expansion snapshot. |
| Platform | Story verification command proves expansion generation/approval stays wired into discovery execution without bypassing campaign or schedule boundaries. |
| Performance | Expansion generation and approved-set reads stay bounded for normal campaign keyword sizes and do not block run creation excessively. |
| Logs/Audit | Generation, edit, approval, replacement, and snapshot-use events remain explainable with actor, campaign, expansion-set, and run/schedule context. |

## Fixtures

- At least one campaign with raw criteria suitable for synonym/abbreviation/
  language expansion.
- One AI-assisted expansion fixture that requires review before approval.
- One user-edited expansion set to prove edited variants can be approved and
  reused.
- One scheduled discovery template that references an approved expansion set.

## Commands

```text
./scripts/verify-us-036.sh
./scripts/bin/harness-cli story verify US-036
```

Proof includes:

- unit tests for grouping and approval rules
- integration tests for expansion persistence and snapshot linkage
- frontend e2e for generate/approve/run flow
- `scripts/bin/harness-cli story verify US-036`

## Acceptance Evidence

- `scripts/bin/harness-cli query matrix` reports `US-036` as **implemented** with
  the expected proof columns populated.
- A representative e2e or integration run shows an approved expansion snapshot
  being used by a discovery job.
- Proof shows AI-generated suggestions cannot be used for first-run execution
  without explicit user review/approval.
