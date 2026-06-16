"""query expansion sets (US-036)

Revision ID: 20260616_0026
Revises: 20260616_0025
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0026"
down_revision: str | Sequence[str] | None = "20260616_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "query_expansion_sets" not in tables:
        op.create_table(
            "query_expansion_sets",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("campaign_id", sa.String(36), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
            sa.Column("generation_mode", sa.String(32), nullable=False, server_default="rule"),
            sa.Column("variants_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_by", sa.String(128), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_by", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_query_expansion_sets_organization_id",
            "query_expansion_sets",
            ["organization_id"],
        )
        op.create_index(
            "ix_query_expansion_sets_campaign_id",
            "query_expansion_sets",
            ["campaign_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "query_expansion_sets" in tables:
        op.drop_table("query_expansion_sets")