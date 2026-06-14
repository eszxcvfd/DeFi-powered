# Validation

## Proof Strategy

The story is done only when the repo has repeatable local commands that prove
the FastAPI backend, Vite frontend, SQLite bootstrap, Dramatiq worker wiring,
and project validation wiring all boot on the accepted baseline. Domain
behavior remains planned, not implemented.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Backend smoke handler, settings parsing, and pure runtime configuration helpers. |
| Integration | Backend starts with SQLite and Redis configuration; worker wiring and migration bootstrap load without domain schema. |
| E2E | Frontend app shell renders and a browser smoke run can verify the first screen when scripts exist. |
| Platform | Local development runtime starts with documented commands for SQLite path creation, Redis, backend, worker, and frontend. |
| Performance | Not required beyond startup responsiveness for the smoke check. |
| Logs/Audit | Request logging shape is visible for the smoke endpoint; product audit remains documented future work. |

## Fixtures

- Local development organization/user fixtures are deferred until auth and
  tenant stories create product data.
- SQLite file path and Redis connection fixtures should be deterministic for
  local and CI runs.

## Commands

Expected verification surface after implementation:

```text
pytest
npm --prefix frontend run build
npm --prefix frontend run test:e2e
docker compose up -d redis
<backend smoke command>
<worker smoke command>
```

## Acceptance Evidence

- `./scripts/verify-foundation.sh` — ruff, pytest, Alembic env, frontend build, vitest shell test, Playwright e2e when browsers install, Redis compose, smoke-api/worker/scheduler/browser-worker.
- Boundaries: `docs/BOUNDARIES.md`.
- Playwright e2e is mandatory (`npm --prefix frontend run test:e2e`). If `playwright install chromium` fails (e.g. Ubuntu 26), `scripts/playwright-install.sh` must resolve system Chrome/Chromium; Vitest is supplementary only.
