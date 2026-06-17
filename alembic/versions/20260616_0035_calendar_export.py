"""Event calendar export (ICS) baseline (US-045) — durable
`calendar_export_tokens` and `calendar_export_audits` tables.
The migration is additive; the documented rollback path is
to drop the new tables. No existing rows are touched.

Revision ID: 20260616_0035
Revises: 20260616_0034
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0035"
down_revision: str | Sequence[str] | None = "20260616_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table_name in set(insp.get_table_names())


def upgrade() -> None:
    if not _has_table("calendar_export_tokens"):
        op.create_table(
            "calendar_export_tokens",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("organization_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("token_hash", sa.String(length=128), nullable=False),
            sa.Column("scope", sa.String(length=32), nullable=False),
            sa.Column("target_id", sa.String(length=36), nullable=True),
            sa.Column("filter_json", sa.Text(), nullable=False, server_default=""),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("audit_correlation_id", sa.String(length=64), nullable=False, server_default=""),
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
            "ix_calendar_export_tokens_org",
            "calendar_export_tokens",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            "ix_calendar_export_tokens_user",
            "calendar_export_tokens",
            ["organization_id", "user_id"],
            unique=False,
        )
        op.create_index(
            "ix_calendar_export_tokens_hash",
            "calendar_export_tokens",
            ["token_hash"],
            unique=False,
        )

    if not _has_table("calendar_export_audits"):
        op.create_table(
            "calendar_export_audits",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("organization_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=True),
            sa.Column("token_id", sa.String(length=36), nullable=True),
            sa.Column("scope", sa.String(length=32), nullable=False),
            sa.Column("event_id", sa.String(length=36), nullable=True),
            sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("result", sa.String(length=32), nullable=False),
            sa.Column("ip_address", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("user_agent", sa.String(length=256), nullable=False, server_default=""),
            sa.Column("request_id", sa.String(length=64), nullable=False, server_default=""),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_calendar_export_audits_org",
            "calendar_export_audits",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            "ix_calendar_export_audits_user",
            "calendar_export_audits",
            ["organization_id", "user_id"],
            unique=False,
        )
        op.create_index(
            "ix_calendar_export_audits_token",
            "calendar_export_audits",
            ["token_id"],
            unique=False,
        )
        op.create_index(
            "ix_calendar_export_audits_result",
            "calendar_export_audits",
            ["organization_id", "result", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("calendar_export_audits"):
        op.drop_table("calendar_export_audits")
    if _has_table("calendar_export_tokens"):
        op.drop_table("calendar_export_tokens")
