"""Performance baseline and SLO guardrails (US-044) —
durable `performance_snapshots` and
`browser_session_samples` tables, plus three new
columns on `browser_sessions` for the budget
enforcement path. The migration also extends the
`alert_rules` table with five seed SLO rules
(`api.read.slo_breach`,
`event.list.pagination.slo_breach`,
`discovery.first_progress.slo_breach`,
`concurrency.cap.slo_breach`,
`browser.session.budget.slo_breach`).

The seed rules are inserted only when the metric
name is not already present in the
`alert_rules` table, so a re-run on a database that
already has the rules is a no-op.

The migration is forward-only; the documented
rollback path is to drop the new tables and the
new columns. No existing rows are touched.

Revision ID: 20260616_0034
Revises: 20260616_0033
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0034"
down_revision: str | Sequence[str] | None = "20260616_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Seed SLO rules from
# `docs/product/performance-baseline-and-slo-guardrails.md`.
# The migration is the single source of truth for the
# seed set so a fresh install gets the rules without
# an extra runtime step. Each entry uses a fixed
# `rule_id` so future re-runs can detect and replace
# existing rows.
SLO_RULES: list[dict[str, object]] = [
    {
        "rule_id": "00000000-0000-4000-8000-000000000b01",
        "name": "api.read.slo_breach",
        "metric": "api.read.latency_ms",
        "operator": "gt",
        "threshold": 500.0,
        "window_seconds": 300,
        "severity": "warning",
        "cooldown_seconds": 600,
        "channels": ["in_app"],
        "sort_order": 110,
    },
    {
        "rule_id": "00000000-0000-4000-8000-000000000b02",
        "name": "event.list.pagination.slo_breach",
        "metric": "event.list.pagination.latency_ms",
        "operator": "gt",
        "threshold": 2000.0,
        "window_seconds": 600,
        "severity": "warning",
        "cooldown_seconds": 600,
        "channels": ["in_app"],
        "sort_order": 120,
    },
    {
        "rule_id": "00000000-0000-4000-8000-000000000b03",
        "name": "discovery.first_progress.slo_breach",
        "metric": "discovery.first_progress_ms",
        "operator": "gt",
        "threshold": 5000.0,
        "window_seconds": 300,
        "severity": "warning",
        "cooldown_seconds": 600,
        "channels": ["in_app"],
        "sort_order": 130,
    },
    {
        "rule_id": "00000000-0000-4000-8000-000000000b04",
        "name": "concurrency.cap.slo_breach",
        "metric": "concurrency.users",
        "operator": "gt",
        "threshold": 100.0,
        "window_seconds": 60,
        "severity": "warning",
        "cooldown_seconds": 600,
        "channels": ["in_app"],
        "sort_order": 140,
    },
    {
        "rule_id": "00000000-0000-4000-8000-000000000b05",
        "name": "browser.session.budget.slo_breach",
        "metric": "browser.session.budget_pct",
        "operator": "gt",
        "threshold": 90.0,
        "window_seconds": 120,
        "severity": "critical",
        "cooldown_seconds": 300,
        "channels": ["in_app", "email"],
        "sort_order": 150,
    },
]


def _seed_organization_id() -> str:
    """The dev workspace id used by the local environment."""

    return "00000000-0000-4000-8000-000000000001"


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns(table_name)}
    return column_name in cols


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table_name in set(insp.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "performance_snapshots" not in tables:
        op.create_table(
            "performance_snapshots",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("organization_id", sa.String(length=36), nullable=False),
            sa.Column("scenario", sa.String(length=64), nullable=False),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "p50_ms", sa.Float(), nullable=False, server_default="0"
            ),
            sa.Column(
                "p95_ms", sa.Float(), nullable=False, server_default="0"
            ),
            sa.Column(
                "p99_ms", sa.Float(), nullable=False, server_default="0"
            ),
            sa.Column(
                "rps", sa.Float(), nullable=False, server_default="0"
            ),
            sa.Column(
                "error_rate",
                sa.Float(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "concurrent_users",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "audit_correlation_id",
                sa.String(length=64),
                nullable=False,
                server_default="",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_performance_snapshots_org",
            "performance_snapshots",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            "ix_performance_snapshots_scenario",
            "performance_snapshots",
            ["scenario"],
            unique=False,
        )

    if "browser_session_samples" not in tables:
        op.create_table(
            "browser_session_samples",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("organization_id", sa.String(length=36), nullable=False),
            sa.Column("session_id", sa.String(length=36), nullable=False),
            sa.Column("profile_id", sa.String(length=36), nullable=False),
            sa.Column(
                "memory_rss_mb",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "cpu_pct",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "budget_pct",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "audited_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "breach",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_browser_session_samples_org",
            "browser_session_samples",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            "ix_browser_session_samples_session_id",
            "browser_session_samples",
            ["session_id"],
            unique=False,
        )

    if "browser_sessions" in tables:
        if not _has_column("browser_sessions", "memory_rss_mb"):
            op.add_column(
                "browser_sessions",
                sa.Column("memory_rss_mb", sa.Integer(), nullable=True),
            )
        if not _has_column("browser_sessions", "cpu_pct"):
            op.add_column(
                "browser_sessions",
                sa.Column("cpu_pct", sa.Integer(), nullable=True),
            )
        if not _has_column("browser_sessions", "budget_breached"):
            op.add_column(
                "browser_sessions",
                sa.Column(
                    "budget_breached",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                ),
            )

    # Insert seed SLO rules. The migration is
    # idempotent: a re-run skips rules that already
    # exist by `metric` name.
    if "alert_rules" in tables:
        org_id = _seed_organization_id()
        for rule in SLO_RULES:
            exists = bind.execute(
                sa.text(
                    "SELECT 1 FROM alert_rules "
                    "WHERE organization_id = :org_id "
                    "AND metric = :metric"
                ),
                {"org_id": org_id, "metric": rule["metric"]},
            ).fetchone()
            if exists:
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO alert_rules ("
                    "id, organization_id, name, metric, operator, threshold, "
                    "window_seconds, severity, cooldown_seconds, channels_json, "
                    "enabled, is_system, sort_order, created_by"
                    ") VALUES ("
                    ":id, :org_id, :name, :metric, :operator, :threshold, "
                    ":window_seconds, :severity, :cooldown_seconds, :channels, "
                    "1, 1, :sort_order, 'system'"
                    ")"
                ),
                {
                    "id": rule["rule_id"],
                    "org_id": org_id,
                    "name": rule["name"],
                    "metric": rule["metric"],
                    "operator": rule["operator"],
                    "threshold": float(rule["threshold"]),
                    "window_seconds": int(rule["window_seconds"]),
                    "severity": rule["severity"],
                    "cooldown_seconds": int(rule["cooldown_seconds"]),
                    "channels": json.dumps(list(rule["channels"])),
                    "sort_order": int(rule["sort_order"]),
                },
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "alert_rules" in tables:
        for rule in SLO_RULES:
            bind.execute(
                sa.text(
                    "DELETE FROM alert_rules "
                    "WHERE organization_id = :org_id "
                    "AND metric = :metric"
                ),
                {"org_id": _seed_organization_id(), "metric": rule["metric"]},
            )
    if "browser_sessions" in tables and _has_column(
        "browser_sessions", "budget_breached"
    ):
        op.drop_column("browser_sessions", "budget_breached")
    if "browser_sessions" in tables and _has_column(
        "browser_sessions", "cpu_pct"
    ):
        op.drop_column("browser_sessions", "cpu_pct")
    if "browser_sessions" in tables and _has_column(
        "browser_sessions", "memory_rss_mb"
    ):
        op.drop_column("browser_sessions", "memory_rss_mb")
    if "browser_session_samples" in tables:
        op.drop_table("browser_session_samples")
    if "performance_snapshots" in tables:
        op.drop_table("performance_snapshots")
