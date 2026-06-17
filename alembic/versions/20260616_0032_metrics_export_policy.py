"""External metrics pipeline baseline (US-042) — durable
`metrics_export_policies` table for the per-workspace
configuration of the Prometheus, OpenTelemetry, and Sentry
sinks. The migration is forward-only; the documented
rollback path is to drop the new table. No other tables,
indexes, or rows are touched.

The new table does not seed any rows; the first slice ships
with the default policy (every sink disabled) and owners or
admins opt in through the policy endpoint.

Revision ID: 20260616_0032
Revises: 20260616_0031
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0032"
down_revision: str | Sequence[str] | None = "20260616_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "metrics_export_policies" in tables:
        return
    op.create_table(
        "metrics_export_policies",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("prometheus_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("otel_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("sentry_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "prometheus_last_status",
            sa.String(length=32),
            nullable=False,
            server_default="disabled",
        ),
        sa.Column("prometheus_last_export_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "otel_last_status",
            sa.String(length=32),
            nullable=False,
            server_default="disabled",
        ),
        sa.Column("otel_last_export_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "sentry_last_status",
            sa.String(length=32),
            nullable=False,
            server_default="disabled",
        ),
        sa.Column("sentry_last_export_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by", sa.String(length=128), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "organization_id",
            name="uq_metrics_export_policies_org",
        ),
    )
    op.create_index(
        "ix_metrics_export_policies_org",
        "metrics_export_policies",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "metrics_export_policies" in tables:
        op.drop_table("metrics_export_policies")
