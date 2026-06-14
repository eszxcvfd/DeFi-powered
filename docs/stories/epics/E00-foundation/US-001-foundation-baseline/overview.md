# Overview

## Current Behavior

The repository contains Harness policy, a baseline SRS in `SPEC.md`, and initial
product docs plus accepted architecture decisions. There is still no
application scaffold, no selected package-manager workflow committed into the
repo, no backend or frontend runtime entrypoint, no Alembic bootstrap, no
SQLite project database path, no Dramatiq worker, and no executable validation
commands for the selected stack.

## Target Behavior

The story should establish the smallest runnable LiveLead foundation:

- FastAPI backend scaffold aligned with `src/livelead/` layering.
- Vite + React + TypeScript frontend scaffold with a minimal app shell using
  `shadcn/ui`.
- Project-local SQLite bootstrap, Alembic initialization, and documented
  database path such as `data/livelead.sqlite3`.
- Dramatiq worker bootstrap with Redis-backed local execution support.
- Health and smoke surfaces that prove backend, frontend, queue, and local
  runtime configuration all boot correctly.
- Initial auth, tenant, RBAC, audit, and source-policy boundaries documented or
  stubbed so later stories cannot bypass them accidentally.
- First validation commands wired into Harness story verification and the test
  matrix.

## Affected Users

- Owner/Admin.
- Analyst.
- Sales/BD.
- Reviewer.
- Viewer.
- Future implementation agents.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/platform-and-automation-policy.md`
- `docs/ARCHITECTURE.md`
- `docs/stories/backlog.md`

## Non-Goals

- Production-ready authentication.
- Domain CRUD and persisted business entities beyond migration/bootstrap needs.
- Domain CRUD for campaigns, events, leads, or connectors.
- Browser automation against live third-party websites.
- AI-generated content.
- CRM integration.
