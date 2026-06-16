# Validation

## Proof Strategy

This story is done only when LiveLead can answer bounded discovery questions
with a structured, grounded copilot response, preserve confidence/assumptions/
risk flags, and let users carry recommendations into discovery prep without
autonomous execution.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Response-schema validation, grounding guards, uncertainty handling, and risk-flag mapping. |
| Integration | Campaign scoping, provider-boundary behavior, structured response persistence or linkage, and accepted recommendation handoff into query expansion/discovery prep. |
| E2E | User asks a natural-language discovery question, sees structured answer sections, and uses a recommendation to prepare a reviewable discovery run. |
| Platform | Story verification command proves copilot response validation stays wired into campaign/discovery prep without bypassing human review or run-creation boundaries. |
| Performance | Bounded copilot requests and recent-response reads stay within acceptable latency for operator planning workflows. |
| Logs/Audit | Request, response, acceptance, rejection, and downstream-linkage events remain explainable with actor, campaign, response id, and redacted provider diagnostics. |

## Fixtures

- At least one campaign with enough criteria/source context to ground a copilot
  response.
- One natural-language question fixture about livestream discovery scope.
- One provider/mock response fixture with low confidence or missing evidence to
  prove uncertainty handling.
- One accepted recommendation fixture that links into query expansion or run
  prep.

## Commands

```text
./scripts/verify-us-037.sh
./scripts/bin/harness-cli story verify US-037
```

## Acceptance Evidence

- `scripts/bin/harness-cli query matrix` reports `US-037` as **implemented** with
  unit, integration, e2e, and platform proof populated.
- A representative e2e or integration run shows a structured discovery-copilot
  response being accepted into a downstream discovery-prep artifact.
- Proof shows copilot output does not trigger direct autonomous discovery
  execution.
