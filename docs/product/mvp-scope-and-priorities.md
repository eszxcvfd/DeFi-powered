# MVP Scope And Priorities

Source: `SPEC.md` sections 1, 2, 5, 11, and 14.

## Product Scope

LiveLead is an interactive web application for finding livestreams, webinars,
online conferences, and hybrid events that may contain qualified leads, then
helping a human operator choose how to interact around them responsibly.

The MVP should stay anchored to these seven core jobs:

1. Receive a market-search brief, natural-language discovery question, and
   ideal customer profile.
2. Discover events from permitted sources.
3. Normalize, deduplicate, and classify event state.
4. Analyze likely attendee groups and score event priority.
5. Create pre-event, in-event, and post-event engagement plans.
6. Suggest comments, questions, direct messages, email, and follow-up content
   for human review.
7. Save leads, activities, stages, and outcomes into the internal pipeline.

Across those jobs, the MVP contract assumes:

- distinct strategies for `UPCOMING`, `LIVE`, and `ENDED` event states
- multi-channel coverage across allowed social, community, email, and website
  surfaces
- intermediary positioning when users are opening opportunities for partner
  businesses
- target-market weighting, with a configurable default focus such as North
  America 50%, China 10%, India 10%, UK 10%

## Priority Rule

When roadmap choices compete, prefer work that directly improves one of the
seven core jobs above before expanding supporting governance or operator-only
surfaces.

## Supporting Capabilities

The following areas are supporting capabilities, not the primary product value
path:

- Source policy, quotas, approval, and secret handling.
- Supervised browser sessions when API, RSS, Atom, sitemap, or ICS access is
  not sufficient.
- Browser-action confirmation, debug artifacts, profile lifecycle, and optional
  engine governance.
- Reporting, export, audit, and operational observability.

These capabilities exist to protect or unblock the core jobs; they do not
change the product into a browser-automation platform or autonomous outreach
tool.

## Non-Negotiable MVP Guardrails

- LiveLead is not an autonomous sales bot.
- Public posting, messaging, and other external communication must remain under
  explicit human review and confirmation.
- External communication defaults to copy/manual handoff or one explicit
  confirmation-gated action at a time; no bulk or autonomous send flows.
- Browser automation is optional, source-aware, and subordinate to permitted
  data-access methods.
- The product must not imply permission to bypass CAPTCHA, MFA, source terms,
  or unauthorized access controls.
