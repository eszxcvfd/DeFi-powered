# Overview

## Current Behavior

`US-001` established the runtime scaffold and `US-002` established campaign and
ICP setup, but the product still lacks a governed source registry. There is no
living product contract for connector policy, no admin connector management
surface, and no durable story packet that defines how a source becomes runnable
or denied before discovery work begins.

## Target Behavior

The story should introduce the first source-registry and policy slice for
LiveLead:

- A product contract and implementation packet for source registry, policy
  fields, approval metadata, and secret-safe management behavior.
- A minimal admin-facing connector registry surface.
- Backend contracts that can represent enabled, disabled, denied, or
  over-budget sources without running discovery yet.
- Policy rules that preserve API or feed preference and secret-redaction
  expectations for later discovery orchestration.

The story prepares connector governance. It does not yet claim live connector
execution, browser login, or event ingestion.

## Affected Users

- Owner/Admin.
- Analyst.
- Future discovery and browser-operation implementation agents.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/platform-and-automation-policy.md`
- `docs/product/source-registry-and-policy.md`
- `docs/product/campaign-and-icp.md`

## Non-Goals

- Running discovery jobs against live sources.
- Implementing headed browser login or storage-state consent flows.
- Full browser recipe authoring and testing.
- Building reporting or connector health dashboards.
