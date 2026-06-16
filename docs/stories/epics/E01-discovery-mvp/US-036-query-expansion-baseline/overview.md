# Overview

## Current Behavior

LiveLead can now run manual and scheduled discovery against real connectors, but
search scope still depends mostly on the raw campaign keywords and brief-derived
criteria. `SPEC.md` explicitly calls for query expansion across synonyms,
abbreviations, languages, and industry phrasing, with user review required when
AI contributes suggestions. There is no dedicated product contract or story
packet yet for governing that expansion layer.

## Target Behavior

This story should establish the first governed query-expansion slice for
LiveLead:

- Generate candidate discovery-query variants from campaign criteria.
- Group variants by type such as synonym, abbreviation, language, and industry
  phrase.
- Require user review/edit approval before first-run use when AI-generated
  suggestions are present.
- Snapshot the approved expansion set into manual and scheduled discovery runs.
- Preserve assumptions/risk markers so later job review can explain what was
  inferred versus directly chosen.

This story should widen discovery coverage without jumping ahead to natural-
language copilot Q&A or autonomous AI-controlled search behavior.

## Affected Users

- Analysts who want broader but still reviewable discovery search coverage.
- Owners/Admins who need AI-assisted discovery expansion to stay bounded and
  explainable.
- Future implementation agents extending discovery copilot, expansion
  effectiveness analysis, or broader multilingual search support.

## Affected Product Docs

- `docs/product/campaign-and-icp.md`
- `docs/product/scheduled-discovery-and-sync.md`
- `docs/product/query-expansion-and-review.md`

## Non-Goals

- Conversational discovery copilot Q&A.
- Autonomous AI query regeneration during a running job.
- Automatic approval of AI-generated expansion with no review step.
- Glossary-management or translation-admin tooling.
- Expansion-effectiveness analytics dashboards.
