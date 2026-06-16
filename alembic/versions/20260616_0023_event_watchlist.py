"""event watchlist tables (US-030)

Revision ID: 20260616_0023
Revises: 20260615_0022
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0023"
down_revision: str | Sequence[str] | None = "20260615_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "event_watchlist_entries" not in tables:
        op.create_table(
            "event_watchlist_entries",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("event_id", sa.String(36), nullable=False),
            sa.Column("reminder_at", sa.String(32), nullable=True),
            sa.Column("reminder_note", sa.String(500), nullable=False, server_default=""),
            sa.Column("last_actor_id", sa.String(128), nullable=False, server_default=""),
            sa.Column("last_actor_role", sa.String(64), nullable=False, server_default=""),
            sa.Column("last_action_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint(
                "organization_id",
                "user_id",
                "event_id",
                name="uq_event_watchlist_user_event",
            ),
        )
        op.create_index(
            "ix_event_watchlist_entries_organization_id",
            "event_watchlist_entries",
            ["organization_id"],
        )
        op.create_index(
            "ix_event_watchlist_entries_user_id", "event_watchlist_entries", ["user_id"]
        )
        op.create_index(
            "ix_event_watchlist_entries_event_id", "event_watchlist_entries", ["event_id"]
        )
        op.create_index(
            "ix_event_watchlist_entries_reminder_at",
            "event_watchlist_entries",
            ["reminder_at"],
        )

    if "event_watchlist_history" not in tables:
        op.create_table(
            "event_watchlist_history",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("event_id", sa.String(36), nullable=False),
            sa.Column("entry_id", sa.String(36), nullable=True),
            sa.Column("action", sa.String(32), nullable=False),
            sa.Column("actor_id", sa.String(128), nullable=False),
            sa.Column("actor_role", sa.String(64), nullable=False, server_default=""),
            sa.Column("from_reminder_at", sa.String(32), nullable=True),
            sa.Column("to_reminder_at", sa.String(32), nullable=True),
            sa.Column("note", sa.String(500), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_event_watchlist_history_organization_id",
            "event_watchlist_history",
            ["organization_id"],
        )
        op.create_index(
            "ix_event_watchlist_history_user_id", "event_watchlist_history", ["user_id"]
        )
        op.create_index(
            "ix_event_watchlist_history_event_id", "event_watchlist_history", ["event_id"]
        )
        op.create_index(
            "ix_event_watchlist_history_action", "event_watchlist_history", ["action"]
        )
        op.create_index(
            "ix_event_watchlist_history_created_at",
            "event_watchlist_history",
            ["created_at"],
        )


def downgrade() -> None:
    op.drop_table("event_watchlist_history")
    op.drop_table("event_watchlist_entries")
