# Generated Content And Safety

Source: `SPEC.md` sections 5.9, 7.2, 12, `UI-005`, and `UC-03`.

## Product Goal

Sales and analyst users need an initial content-studio slice that can turn an
engagement plan into reviewable draft content without sending anything
externally. The product contract must define how LiveLead assembles event and
plan context, lets users choose content parameters, generates multiple draft
variants, preserves generation metadata, and applies anti-spam and
evidence-based safety checks before approval workflow and copy/export stories
arrive.

## MVP Scope

This product slice covers:

- Generating draft content variants from event, score, audience, and engagement
  plan context.
- Letting users choose content type, platform, language, tone, length, market
  context, and CTA settings.
- Showing the context that will be sent to the generation system before
  generation runs.
- Persisting generated drafts with provider or model metadata, input context,
  prompt-template version, and editor attribution.
- Showing risk flags for spammy, unsupported, repetitive, or sensitive-targeted
  drafts.
- Allowing inline editing of generated drafts before they enter a later review
  workflow.

This product slice does not yet cover:

- Reviewer approval workflow and approval history.
- Copy/export behavior or “used” lifecycle transitions.
- Automatic posting, bulk messaging, or browser-assisted sending.
- Feedback learning that changes prompt behavior automatically.
- Lead conversion or pipeline updates.

## Contract Rules

- Generated content must remain a draft artifact until a later approval story
  explicitly changes that lifecycle.
- Every draft must keep generation metadata, including prompt-template version,
  provider or model, input context, output text, and last editor identity.
- The system must expose the context being sent for generation so users can
  validate what information shaped the drafts.
- Risk flags must warn when content is overly promotional, lacks event
  relevance, repeats earlier content, makes unsupported claims, uses an
  unsuitable CTA, or appears to target sensitive attributes.
- Draft generation may use external AI providers, but the product must preserve
  enough metadata to explain what was generated and by which strategy.
- The first content slice may create variants for later review, but it must not
  imply approval, sending, or external execution.
- Generated drafts should remain linked to the event and engagement plan that
  produced them so later reviewers can trace origin and context.

## API Surface

- `POST /content/generate`: create one or more draft variants from an event and
  engagement-plan context using selected generation settings.
- `GET /events/{id}`: return generated-content summaries or equivalent draft
  references needed for event-detail or content-studio navigation.
- Draft payloads must expose content type, platform, settings, output text,
  risk flags, generation metadata, and edit history markers without implying
  approval or sending.

## UI Surface

The MVP generated-content slice should introduce the first part of `UI-005`
without claiming later approval or export behavior:

- Context panel showing event and plan inputs.
- Prompt or setting controls for content type, platform, language, tone,
  length, market, and CTA.
- Multiple draft variants.
- Inline editor for draft refinement.
- Visible risk flags or safety notes beside drafts.

## Validation Implications

- Unit proof should cover generation-request validation, context assembly, risk
  flag rules, and unsupported-action blocking.
- Integration proof should cover draft persistence, metadata storage, risk flag
  persistence, and `POST /content/generate` behavior.
- E2E proof should cover opening a content surface, reviewing context, creating
  variants, and editing at least one draft.
- Logs or audit proof should confirm who generated or edited drafts and which
  provider, model, and template version were used.
- Platform proof should keep generated-content verification wired into the
  Harness matrix for later approval and export stories.
