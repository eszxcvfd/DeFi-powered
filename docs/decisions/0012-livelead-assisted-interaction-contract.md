# 0012 LiveLead Assisted Interaction Contract

Date: 2026-06-14

## Status

Accepted

## Context

`SPEC.md` version 1.1.0 clarified five product-contract points that were only
partially reflected in the architecture and product docs:

- users may begin with a natural-language GenAI brief, not only a structured
  campaign form
- discovery and engagement should span a broader multi-channel surface
- interaction planning must stay structured, including expected result,
  execution basis, and estimated duration
- LiveLead supports an intermediary or middleman business model instead of
  assuming direct service delivery
- public or external communication remains human-reviewed and confirmation-gated

Without a durable decision, the repo could drift back toward a discovery-only
tool or a browser-automation-centric interpretation that weakens the product's
human-in-the-loop position.

## Decision

LiveLead will treat assisted interaction planning as a first-class product
contract, not a side effect of browser automation.

The architecture and product docs must therefore encode these rules:

- A natural-language campaign brief is a valid first input and must be parsed
  into editable structured campaign criteria.
- Campaign scope must support business-model framing and target-market
  weighting, with configurable regional focus.
- Discovery and engagement contracts must support a governed multi-channel
  catalog rather than implying a single platform.
- Engagement playbooks and generated content must be aware of event state
  (`UPCOMING`, `LIVE`, `ENDED`) and preserve `expected_result`,
  `execution_basis`, and `estimated_duration`.
- The product remains human-controlled: public posting, messaging, or other
  external side effects happen only through copy/manual handoff or one explicit
  confirmed action at a time.

## Alternatives Considered

1. Keep the earlier discovery-centric contract and treat GenAI interaction
   planning as optional later polish.
   Rejected because the updated spec makes assisted interaction a core product
   promise rather than an accessory feature.
2. Expand browser automation into a broader autonomous outreach contract.
   Rejected because it conflicts with MVP safety, review, and confirmation
   guardrails.

## Consequences

Positive:

- Architecture, product docs, and future stories share one interpretation of
  the MVP.
- Campaign, discovery, engagement, and content contracts now align around one
  user journey from brief to reviewed interaction.
- Human-in-the-loop guardrails remain explicit even as channel coverage grows.

Tradeoffs:

- More product surfaces now depend on structured AI contracts instead of only
  free-form drafting.
- Future story packets must carry richer data contracts for playbooks, market
  focus, and intermediary positioning.

## Follow-Up

- Update `docs/ARCHITECTURE.md` and affected `docs/product/*.md` files to
  reflect this contract.
- Add or update future stories for natural-language brief parsing, discovery
  copilot, and structured playbook output where implementation is still missing.
- Revisit this decision if MVP scope changes toward autonomous execution or if
  channel coverage is materially narrowed.
