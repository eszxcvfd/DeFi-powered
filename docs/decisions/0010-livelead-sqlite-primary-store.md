# 0010 LiveLead SQLite Primary Store

Date: 2026-06-13

## Status

Accepted

## Context

The project needs a concrete storage baseline for `US-001`. Earlier drafts used
PostgreSQL, but the current direction is to keep the primary database inside
the project itself. The team wants a simpler local-first setup while the
product is still in Foundation and Discovery phases.

## Decision

LiveLead will use a project-local SQLite database file as its primary product
store for the current baseline. The expected location is under the repository,
for example `data/livelead.sqlite3`.

The storage model must preserve these rules:

- SQLite is the source of truth for product records during the current MVP
  baseline.
- The database file lives inside the project tree but is not committed to
  version control.
- SQLAlchemy and Alembic remain the persistence and migration layer so that
  repository and application boundaries stay stable.
- Redis remains available for queueing, caching, rate limits, and locks.
- Large artifacts such as screenshots, HTML snapshots, and exports should stay
  outside SQLite unless there is a small, clear operational reason to embed
  them.

## Alternatives Considered

1. Keep PostgreSQL as the primary store. Rejected because it adds more setup and
   operational surface than the project currently wants.
2. Remove the relational layer and store everything as files. Rejected because
   the product still needs queryable records, constraints, and migrations.

## Consequences

Positive:

- `US-001` can scaffold a simpler environment with fewer required services.
- Local development, demos, and early testing become easier to boot.
- The domain and repository interfaces can stay stable while the storage engine
  remains lightweight.

Tradeoffs:

- Write concurrency and operational scaling are more constrained than a server
  database.
- Some SQL patterns and migration strategies must stay SQLite-compatible.
- Backup and restore must be treated as file-level workflows.

## Follow-Up

- Update architecture, platform policy, stories, and the seed spec to reflect
  the SQLite baseline.
- Add repo-level ignore rules and runtime configuration once implementation
  begins.
- Record a new decision if the project later migrates to PostgreSQL or another
  primary store.
