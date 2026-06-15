# Exec Plan

## Goal

Define and implement the first governed notification layer so LiveLead can
surface in-app alerts, deliver bounded email notifications, and honor
per-user notification preferences for existing reminder, discovery-job, and
event-timing workflows.

## Scope

In scope:

- In-app notifications for discovery job completion, needs-user-action,
  failure, and due/overdue reminders.
- Email notifications for upcoming events, failed jobs, and overdue reminders.
- Per-user notification preferences by type and channel.
- Notification read/dismiss lifecycle.
- Delivery-attempt tracking and suppression behavior.
- Minimal inbox and preference UI.

Out of scope:

- Marketing or outreach email flows.
- Slack, SMS, push, or webhook channels.
- Digest-builder or scheduled-report delivery workflows.
- Watchlist-driven alert automation.
- CRM or ticketing integrations.

## Risk Classification

Risk flags:

- External systems.
- Audit/security.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- External provider behavior.
- Audit/security.

## Work Phases

1. Discovery: confirm notification requirements from `SPEC.md`, reminder,
   discovery-job, and event contracts, plus current user-scope auth behavior.
2. Design: define notification objects, preference rules, delivery adapter
   boundary, and triggering semantics.
3. Validation planning: design proof for in-app inbox state, preference
   enforcement, email delivery attempts, and blocked unauthorized access.
4. Implementation: add the bounded backend generation/delivery flow, inbox and
   preference API, and minimal frontend surfaces.
5. Verification: prove reminder, discovery-job, and event-timing alerts are
   generated correctly and preferences suppress or allow delivery as expected.
6. Harness update: keep product docs current, update durable story proof, and
   leave a clean handoff for watchlist, digest, or external-channel stories.

## Stop Conditions

Pause for human confirmation if:

- Product behavior is ambiguous.
- Data migration or deletion risk appears.
- Validation requirements need to be weakened.
- Architecture direction changes.
- The team wants marketing email, digest scheduling, or webhook fan-out folded
  into this baseline.
- Upcoming-event notification timing requires a product rule that is not yet
  defined in the event contract.
