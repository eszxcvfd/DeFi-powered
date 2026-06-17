"""Connector auto-disable and policy recovery baseline (US-048) —
durable `connector_auto_disable_rules` and
`connector_auto_disable_events` tables, plus the
`Source` extension with
`auto_disabled_at`, `auto_disabled_reason`, and
`auto_disabled_by_event_id` columns. The migration
is additive; the documented rollback path is to
drop the new tables and the new columns. No
existing rows are touched.

Revision ID: 20260616_0038
Revises: 20260616_0037
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0038"
down_revision: str | Sequence[str] | None = "20260616_0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table_name in set(insp.get_table_names())


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if table_name not in set(insp.get_table_names()):
        return False
    columns = {c["name"] for c in insp.get_columns(table_name)}
    return column_name in columns


def upgrade() -> None:
    # Source extension: three read-only columns
    # the bounded `AutoDisableService` updates.
    # Skip the add-column operations when the
    # `sources` table is missing; the base
    # schema migration from `US-003` owns the
    # `sources` table creation.
    if _has_table("sources"):
        if not _has_column("sources", "auto_disabled_at"):
            op.add_column(
                "sources",
                sa.Column(
                    "auto_disabled_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                ),
            )
        if not _has_column("sources", "auto_disabled_reason"):
            op.add_column(
                "sources",
                sa.Column(
                    "auto_disabled_reason",
                    sa.Text(),
                    nullable=True,
                ),
            )
        if not _has_column("sources", "auto_disabled_by_event_id"):
            op.add_column(
                "sources",
                sa.Column(
                    "auto_disabled_by_event_id",
                    sa.String(length=36),
                    nullable=True,
                ),
            )
            op.create_index(
                "ix_sources_auto_disabled_by_event_id",
                "sources",
                ["auto_disabled_by_event_id"],
                unique=False,
            )

    if not _has_table("connector_auto_disable_rules"):
        op.create_table(
            "connector_auto_disable_rules",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "organization_id", sa.String(length=36), nullable=False
            ),
            sa.Column("source_id", sa.String(length=36), nullable=False),
            sa.Column("trigger", sa.String(length=32), nullable=False),
            sa.Column(
                "threshold_value",
                sa.Float(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "window_seconds",
                sa.Integer(),
                nullable=False,
                server_default="1800",
            ),
            sa.Column(
                "consecutive_breaches",
                sa.Integer(),
                nullable=False,
                server_default="3",
            ),
            sa.Column(
                "cooldown_seconds",
                sa.Integer(),
                nullable=False,
                server_default="900",
            ),
            sa.Column(
                "enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column(
                "deleted_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "created_by",
                sa.String(length=128),
                nullable=False,
                server_default="system",
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
            "ix_connector_auto_disable_rules_org",
            "connector_auto_disable_rules",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            "ix_connector_auto_disable_rules_source",
            "connector_auto_disable_rules",
            ["organization_id", "source_id"],
            unique=False,
        )

    if not _has_table("connector_auto_disable_events"):
        op.create_table(
            "connector_auto_disable_events",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "organization_id", sa.String(length=36), nullable=False
            ),
            sa.Column("source_id", sa.String(length=36), nullable=False),
            sa.Column("trigger", sa.String(length=32), nullable=False),
            sa.Column(
                "reason", sa.Text(), nullable=False, server_default=""
            ),
            sa.Column(
                "breach_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "window_start",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.Column(
                "window_end",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.Column(
                "status",
                sa.String(length=16),
                nullable=False,
                server_default="active",
            ),
            sa.Column("alert_event_id", sa.String(length=36), nullable=True),
            sa.Column(
                "health_snapshot_id", sa.String(length=36), nullable=True
            ),
            sa.Column(
                "recovery_actor_id",
                sa.String(length=128),
                nullable=True,
            ),
            sa.Column("recovery_reason", sa.Text(), nullable=True),
            sa.Column(
                "recovered_at", sa.DateTime(timezone=True), nullable=True
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
        )
        op.create_index(
            "ix_connector_auto_disable_events_org",
            "connector_auto_disable_events",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            "ix_connector_auto_disable_events_source",
            "connector_auto_disable_events",
            ["organization_id", "source_id", "created_at"],
            unique=False,
        )
        op.create_index(
            "ix_connector_auto_disable_events_status",
            "connector_auto_disable_events",
            ["organization_id", "status", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("connector_auto_disable_events"):
        op.drop_table("connector_auto_disable_events")
    if _has_table("connector_auto_disable_rules"):
        op.drop_table("connector_auto_disable_rules")
    if _has_column("sources", "auto_disabled_by_event_id"):
        op.drop_index(
            "ix_sources_auto_disabled_by_event_id",
            table_name="sources",
        )
        op.drop_column("sources", "auto_disabled_by_event_id")
    if _has_column("sources", "auto_disabled_reason"):
        op.drop_column("sources", "auto_disabled_reason")
    if _has_column("sources", "auto_disabled_at"):
        op.drop_column("sources", "auto_disabled_at")
