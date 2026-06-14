# Exec Plan

## Goal

Create the first runnable implementation baseline for LiveLead using the
accepted technology stack, without prematurely implementing high-risk domain
behavior.

## Scope

In scope:

- Implement the accepted stack from
  `docs/decisions/0011-livelead-technology-baseline.md`.
- Scaffold a FastAPI backend with typed settings, dependency wiring, and a
  health/smoke endpoint.
- Scaffold a Vite frontend with React, TypeScript, and a minimal `shadcn/ui`
  app shell.
- Bootstrap SQLite persistence, Alembic migration setup, and a documented local
  database path inside the project.
- Bootstrap Dramatiq + Redis local worker wiring.
- Add initial lint, test, build, and smoke commands that future stories can
  reuse.
- Wire the first verification command into the Harness story record.
- Document auth, tenant, RBAC, audit, and source-policy boundaries that later
  stories must preserve.

Out of scope:

- User registration/login flows beyond placeholder boundaries.
- Business entity migrations beyond framework/bootstrap needs.
- Real discovery connectors.
- Browser automation against external sources.
- AI provider integration.
- Production deployment topology beyond local and single-host MVP proof.

## Risk Classification

Risk flags:

- Auth.
- Authorization.
- Data model.
- Audit/security.
- External systems.
- Public contracts.
- Weak proof.
- Multi-domain.

Hard gates:

- Auth.
- Authorization.
- Audit/security.
- External provider behavior.

## Work Phases

1. Scaffold backend package structure, settings, and health surface.
2. Scaffold frontend shell and shared UI baseline.
3. Add SQLite, Alembic, Dramatiq, and Redis local runtime wiring.
4. Add smoke, build, and test commands with deterministic proof.
5. Update Harness verification metadata and product docs if implementation
   reveals a constraint change.

## Stop Conditions

Pause for human confirmation if:

- The accepted technology baseline from `0010` or `0011` needs to change.
- Auth, tenant, or audit requirements need to be weakened.
- A live external provider or browser automation target is introduced.
- Business entity migrations or seed data become necessary in Foundation.
