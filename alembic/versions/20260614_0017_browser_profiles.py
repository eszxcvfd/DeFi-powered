"""browser profiles and session profile link (US-024)

Revision ID: 20260614_0017
Revises: 20260614_0016
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0017"
down_revision: str | Sequence[str] | None = "20260614_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()
    if "browser_profiles" not in tables:
        op.create_table(
            "browser_profiles",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False, index=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("lifecycle_state", sa.String(32), nullable=False, index=True),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("consent_status", sa.String(32), nullable=False, server_default="none"),
            sa.Column("consent_recorded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("consent_actor", sa.String(128), nullable=True),
            sa.Column("state_material_ciphertext", sa.Text(), nullable=True),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
    if "browser_sessions" in tables:
        cols = {c["name"] for c in insp.get_columns("browser_sessions")}
        if "browser_profile_id" not in cols:
            op.add_column(
                "browser_sessions",
                sa.Column("browser_profile_id", sa.String(36), nullable=True, index=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "browser_sessions" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("browser_sessions")}
        if "browser_profile_id" in cols:
            op.drop_column("browser_sessions", "browser_profile_id")
    op.drop_table("browser_profiles")