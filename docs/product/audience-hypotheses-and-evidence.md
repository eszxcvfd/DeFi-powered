# Audience Hypotheses And Evidence

Source: `SPEC.md` sections 5.6, 5.7, 7.2, 12, `UI-004`, and `UC-02`.

## Product Goal

Sales and analyst users need event review and scoring to explain who is likely
to attend an event and why that audience may matter to the campaign. The
product contract must define how LiveLead generates audience hypotheses,
attaches source-backed evidence or clearly labeled inference, blocks sensitive
attribute inference, and exposes a minimal audience review surface before
engagement-plan or feedback-learning workflows arrive.

## MVP Scope

This product slice covers:

- Generating a list of audience hypotheses for a scored canonical event.
- Naming each hypothesis as a potential customer, partner, or referral segment.
- Explaining why a segment is likely relevant using event title, description,
  organizer, speaker, sponsor, tags, and other source-visible cues.
- Linking each audience claim to source evidence or labeling it as model or
  heuristic inference.
- Showing audience hypotheses in event detail with confidence and evidence
  context.
- Preserving enough structured metadata for later user feedback and engagement
  planning stories.

This product slice does not yet cover:

- User feedback that marks a hypothesis correct, incorrect, or uncertain.
- AI-generated engagement plans or content variants.
- Automatic weight learning from audience feedback.
- Person-level attendee discovery or private-profile enrichment.
- Lead creation, outreach, or browser-assisted actions.

## Contract Rules

- Every audience hypothesis must identify a segment rather than a specific
  private person unless that identity is already present in approved, public
  event context.
- Each hypothesis must include a reason and at least one linked evidence item
  or an explicit inference label so users can distinguish observed support from
  derived judgment.
- The product must not infer or expose sensitive attributes such as race,
  religion, health status, sexual orientation, political views, or similar
  protected categories.
- Confidence must communicate uncertainty without overstating certainty when the
  event data is sparse, stale, or indirect.
- Audience hypotheses must remain explainable enough for later audit and review
  and must not depend on hidden connector internals or secret-bearing payloads.
- The first audience slice may use deterministic heuristics, model-assisted
  summaries, or both, but the output must preserve which parts came from
  source-backed evidence and which parts were inferred.
- Audience hypotheses may inform scoring and later engagement work, but this
  story must not blur them into score components or generated content as if
  they were the same artifact.

## API Surface

- `GET /events/{id}`: return audience hypotheses with segment type, fit type,
  reason, evidence summary, inference label, confidence, and generation
  metadata.
- Internal audience-generation flow must persist hypothesis records linked to
  the canonical event without requiring private third-party attendee data.
- If event detail cannot yet populate audience hypotheses, the API must expose a
  clear empty or pending state rather than fabricated placeholders.

## UI Surface

The MVP audience slice should extend `UI-004` without claiming later engagement
behavior:

- Event detail audience tab or equivalent section.
- Hypothesis cards or rows showing segment name, fit type, confidence, and
  reason.
- Evidence summary that distinguishes source-backed observations from inferred
  conclusions.
- Clear empty-state or pending-state messaging when an event has insufficient
  context for reliable hypotheses.

## Validation Implications

- Unit proof should cover audience-rule generation, confidence mapping, and
  sensitive-inference blocking.
- Integration proof should cover persistence of hypotheses and evidence payloads
  plus event-detail API behavior.
- E2E proof should cover opening event detail and reviewing audience hypotheses
  and linked evidence.
- Logs or audit proof should confirm why a hypothesis was generated and whether
  it relied on explicit evidence or labeled inference.
- Platform proof should keep audience verification wired into the Harness
  matrix for later engagement and lead stories.
