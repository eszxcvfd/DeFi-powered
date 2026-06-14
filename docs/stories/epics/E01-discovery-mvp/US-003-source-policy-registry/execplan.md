# Exec Plan

## Goal

Define and implement the minimum governed source-registry slice that lets
LiveLead represent which connectors are allowed to run later, under what policy
conditions, and with what secret-safe admin behavior.

## Scope

In scope:

- Source registry records with connector type, domain, status, policy state,
  authentication mode, rate-limit or budget fields, and approval metadata.
- A source-policy evaluation contract that can decide runnable versus denied
  states before discovery execution starts.
- Secret-handling boundaries for API keys, cookies, and credentials.
- Minimal admin API or UI behavior for managing and reviewing connector
  governance state.
- Audit or log expectations for denied policy decisions and secret-safe handling.

Out of scope:

- Live discovery execution.
- Browser-session creation.
- CAPTCHA, MFA, or consent flows beyond safe-stop and deny rules.
- Event normalization, parsing, or scoring.
- Connector recipe execution against third-party sites.

## Risk Classification

Risk flags:

- External systems.
- Audit/security.
- Public contracts.
- Data model.
- Weak proof.

Hard gates:

- External provider behavior.
- Audit/security.

## Work Phases

1. Discovery: confirm source-policy fields, approval rules, and admin surface
   needs from `SPEC.md` and product docs.
2. Design: define source entities, policy-evaluation rules, secret-handling
   rules, and API/UI contracts without coupling to live connector execution.
3. Validation planning: design unit, integration, E2E, logs/audit, and platform
   proof before implementation starts.
4. Implementation: add registry persistence, policy-state evaluation, secret
   redaction, and minimal admin UI/API surfaces.
5. Verification: prove denied and runnable state decisions, secret-safe output,
   and admin workflow behavior.
6. Harness update: update matrix evidence, product docs, and follow-on story
   assumptions for discovery execution.

## Stop Conditions

Pause for human confirmation if:

- Secret storage requires a provider or encryption mechanism outside the current
  local-first MVP baseline.
- The story needs to introduce live connector execution to make progress.
- Validation requirements for secret redaction, policy denial, or audit evidence
  would need to be weakened.
- Architecture direction changes by moving policy checks out of backend
  commands/queries or by coupling domain logic directly to browser tooling.
