"""audit_entries table (US-026)

Revision ID: 20260614_0019
Revises: 20260614_0018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0019"
down_revision: str | Sequence[str] | None = "20260614_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "audit_entries" not in insp.get_table_names():
        op.create_table(
            "audit_entries",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False, index=True),
            sa.Column("actor_id", sa.String(128), nullable=False, index=True),
            sa.Column("actor_type", sa.String(16), nullable=False, index=True),
            sa.Column("actor_role", sa.String(64), nullable=False, server_default="", index=True),
            sa.Column("action", sa.String(96), nullable=False, index=True),
            sa.Column("action_family", sa.String(48), nullable=False, index=True),
            sa.Column("target_type", sa.String(48), nullable=False, index=True),
            sa.Column("target_id", sa.String(96), nullable=False, index=True),
            sa.Column("target_display", sa.String(300), nullable=False, server_default=""),
            sa.Column("outcome", sa.String(24), nullable=False, index=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, index=True),
            sa.Column("request_id", sa.String(64), nullable=False, server_default="", index=True),
            sa.Column("session_id", sa.String(64), nullable=False, server_default=""),
            sa.Column("correlation_id", sa.String(64), nullable=False, server_default=""),
            sa.Column("client_ip", sa.String(64), nullable=False, server_default=""),
            sa.Column("user_agent", sa.String(300), nullable=False, server_default=""),
            sa.Column("workflow", sa.String(64), nullable=False, server_default=""),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("metadata_redacted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("audit_entries")
