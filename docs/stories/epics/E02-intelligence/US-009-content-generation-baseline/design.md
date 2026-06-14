# Design

## Domain Model

The story should formalize the first generated-content objects:

- `GeneratedContentDraft`: draft artifact linked to an event and engagement
  plan.
- `ContentGenerationRequest`: parameter set for content type, platform,
  language, tone, length, market context, and CTA.
- `ContentRiskFlag`: warning marker for spam, unsupported claims, repetition,
  sensitive targeting, or unsuitable CTA.
- `GenerationMetadata`: provider, model, prompt-template version, input
  context, created-at, and last-editor attribution.

Business rules:

- Drafts remain non-approved artifacts in this story.
- Multiple variants may be created from one generation request.
- Every draft must preserve enough metadata to explain how it was produced.
- Risk flags must remain attached to drafts rather than hidden in logs only.
- Users may edit draft text, but edits must preserve attribution and not erase
  original generation metadata.
- Draft generation must not imply external posting, approval, or browser
  execution.

## Application Flow

Commands:

- Generate draft variants from event and engagement-plan context.
- Persist generated drafts, settings, metadata, and risk flags.
- Update draft text or notes through inline editing.

Queries:

- Get event detail or content-studio view with generated draft summaries.
- Load full draft content with metadata and risk flags.

Generation should live behind a provider abstraction so the initial
implementation can start with one compatible provider without binding product
contracts to vendor-specific details. Content generation should consume plan and
event context without mutating engagement-plan truth.

## Interface Contract

The minimum contract should cover:

- `POST /content/generate` for draft generation.
- `GET /events/{id}` or equivalent content view payload with draft summaries.
- Stable payload fields for content type, platform, generation settings, output
  text, risk flags, provider or model metadata, and last-editor markers.
- Clear empty or not-yet-generated states when an event has no drafts.

Errors should distinguish missing event scope, invalid generation settings,
provider-generation failure, and unavailable planning context without exposing
vendor internals or secrets.

## Data Model

Expected persistence work:

- Add generated-content draft storage linked to events and engagement plans.
- Store settings, output text, risk flags, provider or model metadata, prompt
  template version, and edit attribution.
- Preserve enough lifecycle fields to support future approval stories without
  implementing them fully yet.
- Avoid pulling reviewer-approval or export tables into this story unless only
  placeholder compatibility is strictly needed.

## UI / Platform Impact

- Introduce the first `UI-005` slice with context panel, setting controls,
  variant list, and inline editing.
- Show risk flags clearly next to each draft.
- Keep approval history, copy/export, and external-send actions visibly
  deferred.

## Observability

- Record generation requests, provider failures, draft creation, and draft
  edits in structured logs or audit-friendly traces.
- Keep it diagnosable which context and settings produced a draft.
- Ensure logs avoid leaking secret provider credentials or hidden prompt
  internals that should not surface to users.

## Alternatives Considered

1. Bundle generation and approval into one story. Rejected because the first
   useful vertical slice is draft creation; approval can follow as a separate
   durable workflow.
2. Keep generated drafts ephemeral in the frontend only. Rejected because later
   review, export, and audit flows need persisted drafts and metadata.
