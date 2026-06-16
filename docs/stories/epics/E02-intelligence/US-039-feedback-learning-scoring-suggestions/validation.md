# Validation

## Required Proof

| Layer | Expectation |
| --- | --- |
| Unit | Suggestion generation enforces supported components, safe delta ranges, confidence rules, and no-auto-apply guardrails. |
| Integration | Suggestion sets stay campaign-scoped, preserve decision history, and create a new weight snapshot only after authorized approval. |
| E2E | An authorized user generates a scoring suggestion, reviews current versus proposed weights, approves or rejects it, and sees campaign scoring settings change only on approval. |
| Platform | Story verify command keeps scoring-suggestion APIs, UI review flows, and Harness matrix evidence wired together. |

## Suggested Checks

- Backend unit tests for:
  - Signal-threshold and confidence behavior.
  - Safe delta validation by scoring component.
  - Approval or rejection state transitions.
  - No change to active weights before approval.
- Backend integration tests for:
  - Campaign-scoped suggestion generation.
  - Authorized approval creating a new weight snapshot.
  - Rejection preserving active weights.
  - Audit-log emission or equivalent suggestion-decision tracing.
- Frontend/E2E coverage for:
  - Suggestion panel in campaign scoring settings.
  - Current versus proposed weight comparison.
  - Approval and rejection feedback.
  - Visible messaging that suggestions are advisory until approved.

## Evidence Hooks

- `tests/unit/test_scoring_suggestions.py`
- `tests/integration/test_scoring_suggestions_api.py`
- `tests/integration/test_scoring_suggestions_audit.py`
- `frontend/e2e/scoring-suggestion.spec.ts`
- `scripts/verify-us-039.sh`
- `docs/decisions/0017-scoring-suggestion-feedback-learning-baseline.md`

## Resolved (US-039 implementation)

- Feedback sources: audience incorrect/uncertain (with reason codes) and
  discovery-copilot helpfulness counts, campaign-scoped via event/copilot joins.
- Approval: same roles as scoring weight edits (`require_scoring_editor`: analyst,
  admin, owner).
- Multiple suggestion sets per campaign are allowed; only `pending_review` sets
  may be approved or rejected.
