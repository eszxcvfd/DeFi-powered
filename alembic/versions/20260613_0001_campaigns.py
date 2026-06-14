"""campaigns and dev organization

Revision ID: 20260613_0001
Revises:
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260613_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEV_ORG_ID = "00000000-0000-4000-8000-000000000001"


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("target_industry", sa.String(200), server_default=""),
        sa.Column("product_or_service_focus", sa.String(200), server_default=""),
        sa.Column("market_regions_json", sa.Text(), server_default="[]"),
        sa.Column("languages_json", sa.Text(), server_default="[]"),
        sa.Column("timezone", sa.String(64), server_default="UTC"),
        sa.Column("date_start", sa.String(10), nullable=True),
        sa.Column("date_end", sa.String(10), nullable=True),
        sa.Column("positive_keywords_json", sa.Text(), server_default="[]"),
        sa.Column("exclude_keywords_json", sa.Text(), server_default="[]"),
        sa.Column("icp_json", sa.Text(), server_default="{}"),
        sa.Column("scoring_weights_json", sa.Text(), server_default="{}"),
        sa.Column("status", sa.String(32), server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute(
        sa.text("INSERT INTO organizations (id, name) VALUES (:id, :name)").bindparams(
            id=DEV_ORG_ID, name="LiveLead Dev Organization"
        )
    )


def downgrade() -> None:
    op.drop_table("campaigns")
    op.drop_table("organizations")