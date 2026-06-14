# 0008 LiveLead MVP Baseline

Date: 2026-06-13

## Status

Accepted

## Context

`SPEC.md` defines a high-risk MVP with auth, tenant isolation, source policy,
browser automation, lead data, audit, privacy, AI-generated content, and public
API/UI behavior. The repository currently has Harness but no app scaffold or
living product contract files.

## Decision

Use `SPEC.md` as the seed input, then move ongoing product truth into smaller
Harness artifacts:

- `docs/product/overview.md`
- `docs/product/platform-and-automation-policy.md`
- `docs/stories/backlog.md`
- story packets under `docs/stories/epics/`
- validation state in the Harness durable matrix

For MVP implementation, prefer a modular monolith with Python API/backend
modules, an interactive TypeScript web frontend, a project-local SQLite primary
store, Redis, isolated browser workers, and adapter boundaries for browser and
AI providers.

Treat `docs/ARCHITECTURE.md` as the current implementation guardrail for this
baseline, with deeper boundary detail captured in follow-up architecture
decisions.

## Alternatives Considered

1. Keep extending `SPEC.md` as the living product plan. Rejected because Harness
   expects smaller product docs, story packets, validation proof, and decisions.
2. Scaffold the full app immediately. Rejected because the repo first needs a
   bounded Foundation story and stack decisions before high-risk behavior.

## Consequences

Positive:

- Future work can be story-sized and validated.
- High-risk domains have named boundaries before implementation.
- Product truth can evolve without repeatedly editing a monolithic SRS.

Tradeoffs:

- Initial progress is documentation-heavy.
- Some stack choices remain proposed until the Foundation story confirms them.

## Follow-Up

- Implement the exact backend/frontend/queue/frontend tooling selected in
  `docs/decisions/0011-livelead-technology-baseline.md`.
- Add durable story records and validation expectations for first stories.
- Record accepted follow-up decisions when remaining auth, storage-provider, or
  deployment choices are finalized.
