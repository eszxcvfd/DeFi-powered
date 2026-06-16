"""Observability and alerting baseline (US-041) — alert rules, alert events,
and the seed rule set. The migration is forward-only; the documented
rollback path is to drop the two new tables. No other tables, indexes,
or rows are touched.

Revision ID: 20260616_0031
Revises: 20260616_0030
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0031"
down_revision: str | Sequence[str] | None = "20260616_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Seed rule set documented in docs/product/observability-and-alerting.md and
# docs/decisions/0019-observability-and-alerting-baseline.md. The migration is
# the single source of truth for the seed set so a fresh install gets the
# rules without an extra runtime step. Each entry uses a fixed id (slug) so
# future re-runs can detect and replace existing rows.
SEED_RULES: list[dict[str, object]] = [
    {
        "rule_id": "00000000-0000-4000-8000-000000000a01",
        "name": "backup.stale",
        "metric": "backup.age_hours",
        "operator": "gt",
        "threshold": 26.0,
        "window_seconds": 0,
        "severity": "critical",
        "cooldown_seconds": 3600,
        "channels": ["in_app", "email"],
        "sort_order": 10,
    },
    {
        "rule_id": "00000000-0000-4000-8000-000000000a02",
        "name": "worker.heartbeat.missing",
        "metric": "worker.heartbeat.age_seconds",
        "operator": "gt",
        "threshold": 120.0,
        "window_seconds": 0,
        "severity": "warning",
        "cooldown_seconds": 600,
        "channels": ["in_app"],
        "sort_order": 20,
    },
    {
        "rule_id": "00000000-0000-4000-8000-000000000a03",
        "name": "connector.failure_spike",
        "metric": "connector.failure_rate",
        "operator": "gt",
        "threshold": 0.5,
        "window_seconds": 1800,
        "severity": "warning",
        "cooldown_seconds": 1800,
        "channels": ["in_app"],
        "sort_order": 30,
    },
    {
        "rule_id": "00000000-0000-4000-8000-000000000a04",
        "name": "discovery.needs_user_action_storm",
        "metric": "discovery.needs_user_action_rate",
        "operator": "gt",
        "threshold": 0.3,
        "window_seconds": 3600,
        "severity": "warning",
        "cooldown_seconds": 1800,
        "channels": ["in_app"],
        "sort_order": 40,
    },
    {
        "rule_id": "00000000-0000-4000-8000-000000000a05",
        "name": "browser.crash_loop",
        "metric": "browser.crash_loop",
        "operator": "gte",
        "threshold": 3.0,
        "window_seconds": 600,
        "severity": "critical",
        "cooldown_seconds": 1800,
        "channels": ["in_app", "email"],
        "sort_order": 50,
    },
    {
        "rule_id": "00000000-0000-4000-8000-000000000a06",
        "name": "audit.retention_breach_risk",
        "metric": "audit.retention_breach_risk",
        "operator": "gt",
        "threshold": 90.0,
        "window_seconds": 0,
        "severity": "warning",
        "cooldown_seconds": 86400,
        "channels": ["in_app"],
        "sort_order": 60,
    },
]


def _seed_organization_id() -> str:
    """The dev workspace id used by the local environment and verify scripts.

    The seed rules are workspace-level defaults; a fresh install needs them
    even before the first user signs in, so they belong to the dev
    organization that ships with the project. Production workspaces
    inherit them on demand through the regular rule-management endpoints.
    """

    return "00000000-0000-4000-8000-000000000001"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "alert_rules" not in tables:
        op.create_table(
            "alert_rules",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "organization_id", sa.String(36), nullable=False, index=True
            ),
            sa.Column("name", sa.String(96), nullable=False),
            sa.Column("metric", sa.String(64), nullable=False, index=True),
            sa.Column("operator", sa.String(8), nullable=False),
            sa.Column("threshold", sa.Float(), nullable=False, server_default="0"),
            sa.Column(
                "window_seconds", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column("severity", sa.String(16), nullable=False, server_default="warning"),
            sa.Column(
                "cooldown_seconds", sa.Integer(), nullable=False, server_default="600"
            ),
            sa.Column("channels_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("created_by", sa.String(128), nullable=False, server_default="system"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "organization_id",
                "name",
                name="uq_alert_rules_org_name",
            ),
        )
        op.create_index(
            "ix_alert_rules_metric_enabled",
            "alert_rules",
            ["metric", "enabled"],
        )

    if "alert_events" not in tables:
        op.create_table(
            "alert_events",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "organization_id", sa.String(36), nullable=False, index=True
            ),
            sa.Column("rule_id", sa.String(36), nullable=False, index=True),
            sa.Column("rule_name", sa.String(96), nullable=False),
            sa.Column("metric", sa.String(64), nullable=False),
            sa.Column(
                "fired_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "resolved_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "status", sa.String(16), nullable=False, server_default="firing"
            ),
            sa.Column("severity", sa.String(16), nullable=False, server_default="warning"),
            sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("correlation_id", sa.String(64), nullable=False, server_default=""),
            sa.Column("dedup_key", sa.String(128), nullable=False, index=True),
            sa.Column("acknowledged_by", sa.String(128), nullable=True),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolution_note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_alert_events_org_status_fired_at",
            "alert_events",
            ["organization_id", "status", "fired_at"],
        )

    # Seed the system rules for the dev workspace. The migration is the
    # single source of truth for the seed set so a fresh install gets the
    # rules without an extra runtime step. We use fixed ids and re-runs
    # upsert (replace) the row so the contract is stable.
    bind = op.get_bind()
    org_id = _seed_organization_id()
    for rule in SEED_RULES:
        bind.execute(
            sa.text(
                """
                INSERT INTO alert_rules (
                    id, organization_id, name, metric, operator, threshold,
                    window_seconds, severity, cooldown_seconds, channels_json,
                    enabled, is_system, sort_order, created_by
                ) VALUES (
                    :id, :organization_id, :name, :metric, :operator, :threshold,
                    :window_seconds, :severity, :cooldown_seconds, :channels_json,
                    1, 1, :sort_order, 'system'
                )
                ON CONFLICT(organization_id, name) DO UPDATE SET
                    metric = excluded.metric,
                    operator = excluded.operator,
                    threshold = excluded.threshold,
                    window_seconds = excluded.window_seconds,
                    severity = excluded.severity,
                    cooldown_seconds = excluded.cooldown_seconds,
                    channels_json = excluded.channels_json,
                    enabled = 1,
                    is_system = 1,
                    sort_order = excluded.sort_order
                """
            ),
            {
                "id": rule["rule_id"],
                "organization_id": org_id,
                "name": rule["name"],
                "metric": rule["metric"],
                "operator": rule["operator"],
                "threshold": float(rule["threshold"]),
                "window_seconds": int(rule["window_seconds"]),
                "severity": rule["severity"],
                "cooldown_seconds": int(rule["cooldown_seconds"]),
                "channels_json": json.dumps(list(rule["channels"])),
                "sort_order": int(rule["sort_order"]),
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "alert_events" in tables:
        op.drop_table("alert_events")
    if "alert_rules" in tables:
        op.drop_table("alert_rules")
