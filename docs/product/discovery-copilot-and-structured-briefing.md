# Discovery Copilot And Structured Briefing

Source: `SPEC.md` sections 5.2, 5.4, 9.3, 9.4, 12, 14.1, and `UI-002`.

## Product Goal

Analysts need a natural-language discovery copilot that can turn fuzzy
livestream questions into a reviewable discovery plan instead of forcing every
search refinement through manual field editing. The product contract should
define the first governed discovery-copilot slice that accepts bounded natural-
language questions, grounds responses in campaign/source context, and returns a
structured answer with claims, evidence, confidence, assumptions, risk flags,
and recommended discovery queries or sources.

## MVP Scope

This product slice covers:

- Accepting natural-language discovery questions tied to a campaign or explicit
  discovery context.
- Returning a structured copilot response that includes proposed query framing,
  recommended source scope, assumptions, risk flags, confidence, and evidence
  summary.
- Reusing the existing query-expansion layer when the copilot recommends search
  variants rather than inventing a separate keyword system.
- Keeping copilot output reviewable and editable before it becomes a manual or
  scheduled discovery run.
- Preserving enough copilot provenance to explain which prompt/context produced
  a structured recommendation.

This product slice does not yet cover:

- Autonomous execution of discovery runs directly from an unreviewed copilot
  answer.
- Multi-turn memory that persists as a long-lived autonomous agent workspace.
- Playbook/content generation or outreach advice beyond bounded discovery
  planning.
- Generic open-domain chat unrelated to the current campaign/discovery context.
- Feedback loops, ranking analytics, or automated learning from thumbs up/down.

## Contract Rules

- Discovery copilot must stay grounded in selected campaign criteria, approved
  sources, existing discovery data, and other allowed product context; it must
  not answer from arbitrary unrelated world knowledge.
- Copilot output for analysis/planning must follow a structured schema that at
  minimum preserves `claims`, `evidence`, `confidence`, `assumptions`, and
  `risk_flags`.
- When the copilot recommends search variants or query framing, that output
  must remain reviewable through the query-expansion/discovery-prep surfaces
  rather than silently executing.
- Low-confidence or under-supported answers are valid; the copilot must express
  uncertainty instead of fabricating certainty.
- Risk flags must surface issues such as weak evidence, unsupported claims,
  sensitive-inference risk, or missing source coverage when relevant.
- The first copilot slice must remain human-controlled: users can accept,
  revise, or ignore recommendations before run creation.
- Copilot requests and responses must remain tenant-scoped and secret-safe; raw
  secrets, provider credentials, and protected internals must never appear in
  the answer payload.

## API Surface

Implemented routes (US-037):

- `POST /campaigns/{id}/discovery-copilot:respond` — bounded natural-language
  question; returns structured `claims`, `evidence`, `confidence`, `assumptions`,
  `risk_flags`, `proposed_query_framing`, `recommended_source_ids`.
- `GET /campaigns/{id}/discovery-copilot/responses` — recent campaign-scoped
  history.
- `POST /campaigns/{id}/discovery-copilot:accept` — links one response into a
  new **query-expansion** set (`pending_review`); does not create discovery jobs.

Manual-run, schedule, and query-expansion flows may reference accepted copilot
recommendations; copilot does not own discovery execution APIs in this slice.

### Runtime provider (implementation)

- **Default in tests/CI:** `LIVELEAD_DISCOVERY_COPILOT_PROVIDER=deterministic`
  (template provider, no external API).
- **Operator / Gemini:** `LIVELEAD_DISCOVERY_COPILOT_PROVIDER=gemini` with
  `LIVELEAD_GOOGLE_AI_STUDIO_API_KEY` and `LIVELEAD_GEMINI_MODEL` (e.g.
  `gemini-2.0-flash`). Requires `google-genai` in the API virtualenv.
- Provider output is **normalized** then **schema-validated**; API keys and
  secrets never appear in response payloads or audit metadata shown to clients.

Configuration detail: `docs/RUNTIME_CONFIGURATION.md`.

## UI Surface

- Campaign/discovery prep surfaces can open a bounded copilot panel for natural-
  language discovery questions.
- Copilot responses show structured sections for proposed query framing,
  recommended sources, evidence/confidence, assumptions, and risk flags.
- Users can take a structured recommendation into query expansion or discovery
  prep rather than copying opaque chat text manually.
- The first UX should feel like a guided planner, not an autonomous assistant
  that bypasses review controls.

## Validation Implications

- Unit proof should cover response-schema validation, uncertainty handling,
  grounding constraints, and risk-flag mapping.
- Integration proof should cover campaign scoping, provider-boundary behavior,
  structured response persistence if used, and safe linkage into query-expansion
  or discovery-prep flows.
- E2E proof should cover asking a natural-language discovery question, seeing a
  structured answer, and using it to prepare a reviewable discovery run without
  autonomous execution.
- Logs and audit proof should confirm who asked which discovery question, which
  context grounded the answer, and what structured recommendation was returned
  without leaking secrets.
- Platform proof should keep copilot verification wired into the Harness matrix
  before broader AI feedback/learning or multi-turn memory stories widen scope.

## Implementation status

- **US-037 implemented:** API, persistence, campaign UI panel, Gemini + deterministic
  providers, accept → query expansion handoff.
- **Proof:** `./scripts/verify-us-037.sh`, `frontend/e2e/discovery-copilot.spec.ts`,
  `scripts/bin/harness-cli story verify US-037`.
