# Runtime configuration

LiveLead loads environment variables from the **repo-root** `.env` file (copy
from `.env.example`). All application settings use the `LIVELEAD_` prefix and
are defined in `src/livelead/runtime/settings.py`. Workers and the scheduler
also read `.env` via `src/livelead/runtime/env_bootstrap.py` regardless of
current working directory.

| File | Purpose |
| --- | --- |
| `.env` | Local secrets and overrides (gitignored) |
| `.env.example` | Full template with defaults and empty optional fields |
| `frontend/.playwright-browser.env` | Optional Chrome path from `scripts/playwright-install.sh` |

After changing `.env`, **restart** the API process and the Dramatiq worker;
they do not hot-reload configuration.

## Discovery copilot (US-037)

Campaign detail → **Discovery copilot** uses a provider selected by
`LIVELEAD_DISCOVERY_COPILOT_PROVIDER`:

| Value | Behavior |
| --- | --- |
| `gemini` | Calls **Google AI Studio** (Gemini) using `LIVELEAD_GOOGLE_AI_STUDIO_API_KEY` |
| `deterministic` | Local template responses (tests/CI; no API key) |

Required for Gemini in production-like local use:

```env
LIVELEAD_DISCOVERY_COPILOT_PROVIDER=gemini
LIVELEAD_GOOGLE_AI_STUDIO_API_KEY=<from https://aistudio.google.com/apikey>
LIVELEAD_GEMINI_MODEL=gemini-2.0-flash
```

Use a model id supported by the GenAI API (e.g. `gemini-2.0-flash`,
`gemini-2.5-flash`). Custom or preview model names may return API errors.

The Python package `google-genai` is a **core dependency** (`pip install -e ".[dev]"`).
Run API and worker with the project `.venv` so the SDK is available.

**Response handling:** Gemini output is normalized to the structured copilot
schema (`claims`, `evidence`, `confidence`, `assumptions`, `risk_flags`,
`proposed_query_framing`, `recommended_source_ids`) before persistence. Incomplete
model JSON may receive fallback claims and `weak_evidence` / `low_confidence`
risk flags — operators should review before **Send framing to query expansion**.

**API routes:**

- `POST /campaigns/{id}/discovery-copilot:respond`
- `GET /campaigns/{id}/discovery-copilot/responses`
- `POST /campaigns/{id}/discovery-copilot:accept` → creates a **pending_review**
  query-expansion set (US-036); does not run discovery.

Product contract: `docs/product/discovery-copilot-and-structured-briefing.md`.

## Query expansion (US-036)

Governed keyword variants and approval before discovery runs with expanded
queries. Copilot **accept** hands off proposed framing into this layer.

Discovery jobs honor `use_expansion` on create; unapproved AI expansion blocks
run with HTTP 409 until the set is approved on the campaign detail panel.

Product contract: `docs/product/query-expansion-and-review.md`.

## Verification

| Story | Command |
| --- | --- |
| US-036 | `./scripts/verify-us-036.sh` |
| US-037 | `./scripts/verify-us-037.sh` |
| Matrix | `scripts/bin/harness-cli query matrix` |

Tests force `LIVELEAD_DISCOVERY_COPILOT_PROVIDER=deterministic` in
`tests/conftest.py` so CI does not require a Gemini key.

## Related docs

- `docs/FOUNDATION_RUNTIME.md` — processes, browser, discovery feeds
- `docs/TEST_MATRIX.md` — story proof columns
- `docs/product/README.md` — product contract index