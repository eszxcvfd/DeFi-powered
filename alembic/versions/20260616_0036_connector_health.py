"""Connector health surface baseline (US-046) — durable
`connector_health_snapshots` and `connector_health_errors`
tables. The migration is additive; the documented
rollback path is to drop the new tables. No
existing rows are touched.

Revision ID: 20260616_0036
Revises: 20260616_0035
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0036"
down_revision: str | Sequence[str] | None = "20260616_0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table_name in set(insp.get_table_names())


def upgrade() -> None:
    if not _has_table("connector_health_snapshots"):
        op.create_table(
            "connector_health_snapshots",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("organization_id", sa.String(length=36), nullable=False),
            sa.Column("source_id", sa.String(length=36), nullable=False),
            sa.Column("connector_type", sa.String(length=32), nullable=False),
            sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
            sa.Column("total_runs", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("success_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("p50_latency_ms", sa.Float(), nullable=False, server_default="0"),
            sa.Column("p95_latency_ms", sa.Float(), nullable=False, server_default="0"),
            sa.Column("captcha_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("captcha_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error_code", sa.String(length=64), nullable=True),
            sa.Column("last_error_message", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="unknown"),
            sa.Column("audit_correlation_id", sa.String(length=64), nullable=False, server_default=""),
            sa.Column(
                "computed_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
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
            "ix_connector_health_snapshots_org",
            "connector_health_snapshots",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            "ix_connector_health_snapshots_source",
            "connector_health_snapshots",
            ["organization_id", "source_id", "computed_at"],
            unique=False,
        )
        op.create_index(
            "ix_connector_health_snapshots_status",
            "connector_health_snapshots",
            ["organization_id", "status", "computed_at"],
            unique=False,
        )

    if not _has_table("connector_health_errors"):
        op.create_table(
            "connector_health_errors",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("organization_id", sa.String(length=36), nullable=False),
            sa.Column("source_id", sa.String(length=36), nullable=False),
            sa.Column("error_code", sa.String(length=64), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=False),
            sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("audit_correlation_id", sa.String(length=64), nullable=False, server_default=""),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_connector_health_errors_org",
            "connector_health_errors",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            "ix_connector_health_errors_source",
            "connector_health_errors",
            ["organization_id", "source_id", "last_seen_at"],
            unique=False,
        )
        op.create_index(
            "ix_connector_health_errors_code",
            "connector_health_errors",
            ["organization_id", "error_code"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("connector_health_errors"):
        op.drop_table("connector_health_errors")
    if _has_table("connector_health_snapshots"):
        op.drop_table("connector_health_snapshots")
