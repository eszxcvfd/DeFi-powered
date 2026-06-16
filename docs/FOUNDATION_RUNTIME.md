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
./scripts/install-browser-runtime.sh   # Playwright Python + Chromium for real browser sessions (US-020)
```

### Real browser sessions (US-020)

Default API runtime uses **Playwright** (`LIVELEAD_BROWSER_AUTOMATION_MODE=playwright`): each session opens an isolated Chromium context and navigates to the event URL (read-only; no form actions).

- `LIVELEAD_BROWSER_AUTOMATION_MODE=stub` — tests/CI only (no Chromium).
- `LIVELEAD_PLAYWRIGHT_CHROMIUM_EXECUTABLE` — system Chrome (see `scripts/playwright-install.sh`).
- `LIVELEAD_CLOAKBROWSER_EXECUTABLE` — CloakBrowser binary (e.g. `/usr/local/bin/cloakbrowser`) when connector `automation_engine` is `cloakbrowser`.
- `LIVELEAD_BROWSER_HEADLESS=false` — headed window for local supervision.

**Config files (paths):**

| File | Location |
| --- | --- |
| Main app env | **Repo root** `.env` (copy from `.env.example`) |
| Full variable list | `.env.example` + `docs/RUNTIME_CONFIGURATION.md` |
| Chrome path (auto) | `frontend/.playwright-browser.env` (created by `./scripts/playwright-install.sh`) |

Restart API and worker after editing `.env`.

If you see `Executable doesn't exist at .../ms-playwright/chromium_headless_shell-...`, set `LIVELEAD_PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/google-chrome-stable` in root `.env` or run `./scripts/playwright-install.sh`, then restart the API.

### Real discovery (RSS/Atom/ICS)

Campaign **Run discovery** fetches real feeds when `LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS=false` (default in repo-root `.env`). Settings load from that file even if the worker was started from another directory (`env_bootstrap.load_repo_dotenv`). **Restart the dramatiq worker** after changing `.env` — workers do not hot-reload config. Known domains map to public RSS URLs (`src/livelead/infrastructure/connectors/feed_urls.py`); override per source via Admin `rate_limit_json`: `{"feed_url": "https://..."}`. Items are filtered by campaign positive/exclude keywords. Tests set `LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS=true`. Fixture titles (B2B Payments Webinar, SaaS Growth Meetup, …) only come from mock mode or `*-mock.example.com` sources.

### Query expansion and discovery copilot (US-036 / US-037)

On **Campaign detail**, operators can generate and approve **query expansion**
variants and ask the **discovery copilot** (natural-language planning). Copilot
acceptance projects framing into query expansion; neither path auto-starts
discovery.

For Gemini copilot locally, set `LIVELEAD_DISCOVERY_COPILOT_PROVIDER=gemini`
and `LIVELEAD_GOOGLE_AI_STUDIO_API_KEY` in repo-root `.env`. See
`docs/RUNTIME_CONFIGURATION.md` for model ids, SDK, and verify scripts
(`./scripts/verify-us-036.sh`, `./scripts/verify-us-037.sh`).

## Process entrypoints

| Process | Command |
| --- | --- |
| web-api | `uvicorn apps.api.main:app` |
| worker | `./scripts/run-worker.sh` (wraps `dramatiq apps.worker.tasks`) |
| scheduler | `python -m apps.scheduler.main` |
| browser-worker | `python -m apps.browser_worker.main` |
| frontend | `npm --prefix frontend run dev` |

## Open decisions

See `docs/ARCHITECTURE.md` — authentication mechanism, object storage provider, CloakBrowser approval remain open.