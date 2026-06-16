# Agent Instructions

## LiveLead Notes

- Product source of truth order for this repo is: `SPEC.md` -> accepted records
  in `docs/decisions/` -> `docs/product/*.md` -> the selected story packet in
  `docs/stories/epics/`. Do not let chat history override those files.
- Preserve the modular-monolith boundaries in `docs/ARCHITECTURE.md`. Keep
  domain and application logic free from FastAPI, SQLAlchemy, Playwright,
  Redis, and vendor SDK imports; framework wiring belongs in
  `src/livelead/infrastructure/`, `src/livelead/interfaces/`, and `apps/`.
- The implementation baseline is Python/FastAPI + SQLAlchemy/Alembic +
  project-local SQLite, Dramatiq/Redis, and React/TypeScript/Vite. New work
  should extend that baseline rather than introducing parallel stacks.
- Before creating a new story, always check `scripts/bin/harness-cli query
  matrix` and the relevant `docs/product/*.md` file first. If a surface already
  has a product contract or story packet, update it instead of creating a
  duplicate.
- Keep exactly one canonical story path per `US-xxx`. If the same story id
  appears in more than one folder, treat that as drift and update the canonical
  packet rather than creating another copy.
- When behavior changes, update the affected product doc, the story packet,
  durable story status in Harness, and add a decision record whenever auth,
  authorization, data ownership, API shape, or validation rules materially
  change.
- For auth/admin/notification work, prefer the existing contracts in
  `docs/product/identity-and-access.md`,
  `docs/product/member-management-and-access-governance.md`, and
  `docs/product/notification-delivery-and-preferences.md` before redefining the
  surface.
- Local runtime and secrets: repo-root `.env` from `.env.example`; copilot
  (Gemini), query expansion, and verify scripts are documented in
  `docs/RUNTIME_CONFIGURATION.md` and `docs/FOUNDATION_RUNTIME.md`.
- For discovery query expansion and copilot, prefer
  `docs/product/query-expansion-and-review.md` and
  `docs/product/discovery-copilot-and-structured-briefing.md` (US-036/037
  implemented).

<!-- HARNESS:BEGIN -->
## Harness

This repo uses Harness. Before work, read:

- `README.md`
- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `docs/ARCHITECTURE.md`
- `docs/CONTEXT_RULES.md`
- `scripts/bin/harness-cli query matrix` on macOS/Linux, or `.\scripts\bin\harness-cli.exe query matrix` on Windows

Use the Rust Harness CLI at `scripts/bin/harness-cli` on macOS/Linux or
`scripts/bin/harness-cli.exe` on Windows as the main operational tool.
<!-- HARNESS:END -->
