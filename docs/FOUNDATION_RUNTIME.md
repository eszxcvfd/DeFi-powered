# Foundation runtime (US-001)

Local commands for the accepted technology baseline (`0011`).

## Prerequisites

- Python 3.12+
- Node.js 20+ (frontend)
- Docker Compose (Redis)
- Playwright e2e: mandatory. Two different things:
  - **Bundled Chromium** (`playwright install chromium`) — Playwright’s download; often
    **fails on Ubuntu 26** with “does not support chromium on ubuntu26.04”. That is normal.
  - **Google Chrome you installed** — still works. `scripts/playwright-install.sh` sets
    `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to `/usr/bin/google-chrome-stable` (or similar).

## Paths

- SQLite: `data/livelead.sqlite3` (gitignored; created on API boot)
- Redis: `redis://127.0.0.1:6379/0` (override with `LIVELEAD_REDIS_URL`)

## Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
docker compose up -d redis
uvicorn apps.api.main:app --reload --app-dir .  # PYTHONPATH=src
dramatiq apps.worker.tasks --processes 1 --threads 1  # PYTHONPATH=src, Redis up
npm --prefix frontend install && npm --prefix frontend run dev
./scripts/verify-foundation.sh
```

Set `PYTHONPATH=src` (or export from your shell profile) when running API and worker from the repo root.

## Enforcement boundaries (stubs)

See `docs/BOUNDARIES.md` and `src/livelead/boundaries/` (auth, tenant, RBAC, audit, source policy) plus `src/livelead/domain/placeholders.py`.

## Smoke and verify

```bash
./scripts/verify-foundation.sh   # full US-001 proof; Playwright e2e is mandatory
./scripts/playwright-install.sh    # bundled chromium or system browser path
./scripts/smoke-api.sh
./scripts/smoke-worker.sh        # requires Redis
./scripts/smoke-scheduler.sh
./scripts/smoke-browser-worker.sh
```

## Process entrypoints

| Process | Command |
| --- | --- |
| web-api | `uvicorn apps.api.main:app` |
| worker | `dramatiq apps.worker.tasks` |
| scheduler | `python -m apps.scheduler.main` |
| browser-worker | `python -m apps.browser_worker.main` |
| frontend | `npm --prefix frontend run dev` |

## Open decisions

See `docs/ARCHITECTURE.md` — authentication mechanism, object storage provider, CloakBrowser approval remain open.