"""event manual override and change history tables (US-031)

Revision ID: 20260616_0024
Revises: 20260616_0023
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0024"
down_revision: str | Sequence[str] | None = "20260616_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "event_manual_overrides" not in tables:
        op.create_table(
            "event_manual_overrides",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("event_id", sa.String(36), nullable=False),
            sa.Column("field", sa.String(64), nullable=False),
            sa.Column("source_backed_value", sa.Text(), nullable=False, server_default=""),
            sa.Column("override_value", sa.Text(), nullable=False, server_default=""),
            sa.Column("value_kind", sa.String(16), nullable=False, server_default="text"),
            sa.Column("note", sa.String(500), nullable=False, server_default=""),
            sa.Column("actor_id", sa.String(128), nullable=False),
            sa.Column("actor_role", sa.String(64), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint(
                "organization_id",
                "event_id",
                "field",
                name="uq_event_manual_overrides_event_field",
            ),
        )
        op.create_index(
            "ix_event_manual_overrides_organization_id",
            "event_manual_overrides",
            ["organization_id"],
        )
        op.create_index(
            "ix_event_manual_overrides_event_id", "event_manual_overrides", ["event_id"]
        )
        op.create_index(
            "ix_event_manual_overrides_field", "event_manual_overrides", ["field"]
        )

    if "event_change_history" not in tables:
        op.create_table(
            "event_change_history",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("event_id", sa.String(36), nullable=False),
            sa.Column("action", sa.String(32), nullable=False),
            sa.Column("field", sa.String(64), nullable=False),
            sa.Column("value_kind", sa.String(16), nullable=False, server_default="text"),
            sa.Column("prior_value", sa.Text(), nullable=False, server_default=""),
            sa.Column("new_value", sa.Text(), nullable=False, server_default=""),
            sa.Column("source_backed_value", sa.Text(), nullable=False, server_default=""),
            sa.Column("actor_id", sa.String(128), nullable=False),
            sa.Column("actor_role", sa.String(64), nullable=False, server_default=""),
            sa.Column("reason", sa.String(500), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_event_change_history_organization_id",
            "event_change_history",
            ["organization_id"],
        )
        op.create_index(
            "ix_event_change_history_event_id", "event_change_history", ["event_id"]
        )
        op.create_index(
            "ix_event_change_history_action", "event_change_history", ["action"]
        )
        op.create_index(
            "ix_event_change_history_created_at",
            "event_change_history",
            ["created_at"],
        )


def downgrade() -> None:
    op.drop_table("event_change_history")
    op.drop_table("event_manual_overrides")
