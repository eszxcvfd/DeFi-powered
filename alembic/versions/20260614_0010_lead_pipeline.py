"""lead pipeline and activity history

Revision ID: 20260614_0010
Revises: 20260614_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0010"
down_revision: str | Sequence[str] | None = "20260614_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()
    if "leads" not in tables:
        op.create_table(
            "leads",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False, index=True),
            sa.Column("campaign_id", sa.String(36), nullable=True, index=True),
            sa.Column("display_name", sa.String(300), nullable=False),
            sa.Column("company", sa.String(300), server_default=""),
            sa.Column("title", sa.String(200), server_default=""),
            sa.Column("public_url", sa.String(1024), server_default=""),
            sa.Column("discovery_source", sa.String(200), server_default=""),
            sa.Column("event_id", sa.String(36), nullable=True, index=True),
            sa.Column("interests", sa.Text(), server_default=""),
            sa.Column("pain_points", sa.Text(), server_default=""),
            sa.Column("owner", sa.String(128), server_default=""),
            sa.Column("stage", sa.String(32), server_default="newly_discovered", index=True),
            sa.Column("lawful_basis_note", sa.Text(), server_default=""),
            sa.Column("follow_up_date", sa.String(10), nullable=True),
            sa.Column("notes", sa.Text(), server_default=""),
            sa.Column("manual_entry_note", sa.Text(), server_default=""),
            sa.Column("origin_kind", sa.String(32), server_default="event"),
            sa.Column("email_hash", sa.String(64), server_default="", index=True),
            sa.Column("external_id", sa.String(128), server_default="", index=True),
            sa.Column("created_by", sa.String(128), server_default="analyst"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
    if "lead_activities" not in tables:
        op.create_table(
            "lead_activities",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("lead_id", sa.String(36), nullable=False, index=True),
            sa.Column("kind", sa.String(32), nullable=False),
            sa.Column("actor", sa.String(128), nullable=False),
            sa.Column("body", sa.Text(), server_default=""),
            sa.Column("from_stage", sa.String(32), server_default=""),
            sa.Column("to_stage", sa.String(32), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("lead_activities")
    op.drop_table("leads")
