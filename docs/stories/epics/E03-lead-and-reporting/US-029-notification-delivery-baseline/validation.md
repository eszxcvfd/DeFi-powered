# Validation

## Proof Strategy

This story is done only when LiveLead can create user-scoped in-app
notifications, attempt bounded email deliveries, honor notification preference
settings, and keep every notification source and delivery outcome explainable
without leaking provider secrets.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Candidate-generation rules, preference filtering, unread/read/dismiss state transitions, upcoming-event timing eligibility, and delivery suppression rules. |
| Integration | Notification inbox persistence, preference reads/updates, reminder/job/event trigger paths, email-delivery attempt recording, tenant scoping, and unauthorized cross-user access denial. |
| E2E | User sees a new in-app alert, marks it read or dismissed, changes preferences, and confirms future notification behavior reflects the updated settings. |
| Platform | Story verification command proves backend, frontend, and notification adapter fixtures succeed without weakening auth, reminder, or discovery-job proof paths. |
| Performance | Inbox queries remain bounded for normal user volumes, and duplicate notification generation is controlled for repeated job or reminder transitions. |
| Logs/Audit | Preference changes, state transitions, delivery attempts, suppressions, and provider failures create explainable logs/audit evidence without leaking secrets. |

## Fixtures

- At least one user with active membership and email-capable preference state.
- One reminder fixture that becomes due or overdue.
- One discovery job fixture that completes, fails, or needs user action.
- One event fixture with a trustworthy upcoming start time.
- One provider adapter fixture for successful delivery and one for failed or
  suppressed delivery.

## Commands

Add commands after scripts exist.

```text
TBD
Suggested: ./scripts/verify-us-029.sh
Suggested: scripts/bin/harness-cli story verify US-029
```

## Acceptance Evidence

Add results after verification.
