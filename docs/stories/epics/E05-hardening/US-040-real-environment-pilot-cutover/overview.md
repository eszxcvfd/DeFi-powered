# Overview

## Current Behavior

LiveLead now has broad MVP coverage and a growing matrix of implemented
features, but the repo still behaves primarily like a test or local-validation
system. Many flows assume local `.env` management, dev-friendly runtime
defaults, and proof through verify scripts rather than a governed live
environment with rollout, backup, rollback, and operator launch controls. The
project needs an urgent cutover path into a real environment so teams can run
actual campaigns and connectors instead of staying trapped in test-only mode.

## Target Behavior

This story should establish the first real-environment pilot cutover slice for
LiveLead:

- Define one governed pilot-live environment for the existing modular-monolith
  stack.
- Separate test defaults from live runtime settings and disable dev-only trust
  paths.
- Gate live connectors, AI providers, notifications, and risky external actions
  behind explicit enablement controls.
- Add readiness, backup, rollback, and post-cutover verification requirements.
- Provide the minimum operator-facing runbook and runtime status needed to go
  live safely and pause quickly if something goes wrong.

This story should move the system from “works in test/local proof” to “can be
operated in a real environment” without claiming full HA, multi-region, or
large-scale production maturity.

## Affected Users

- Owners and Admins responsible for launching the first real operator
  environment.
- Analysts and Sales/BD users who need the current MVP to run against real
  campaigns, real connectors, and real data.
- Future implementation agents extending observability, performance, security,
  or larger-scale production operations.

## Affected Product Docs

- `docs/product/real-environment-cutover-and-live-operations.md`
- `docs/product/platform-and-automation-policy.md`
- `docs/product/source-registry-and-policy.md`
- `docs/product/identity-and-access.md`
- `docs/product/notification-delivery-and-preferences.md`
- `docs/ARCHITECTURE.md`
- `docs/RUNTIME_CONFIGURATION.md`

## Non-Goals

- Full enterprise production platform design.
- Zero-downtime release orchestration or blue/green traffic switching.
- Kubernetes migration or distributed service decomposition.
- Fully automated autoscaling and cost optimization.
- Broad performance tuning beyond the first live guardrails and critical checks.
