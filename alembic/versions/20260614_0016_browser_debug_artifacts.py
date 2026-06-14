"""browser debug artifacts (US-023)

Revision ID: 20260614_0016
Revises: 20260614_0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0016"
down_revision: str | Sequence[str] | None = "20260614_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "browser_debug_artifacts" not in insp.get_table_names():
        op.create_table(
            "browser_debug_artifacts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("session_id", sa.String(36), nullable=False, index=True),
            sa.Column("organization_id", sa.String(36), nullable=False, index=True),
            sa.Column("artifact_type", sa.String(32), nullable=False),
            sa.Column("capture_mode", sa.String(32), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("storage_path", sa.String(1024), nullable=False),
            sa.Column("content_type", sa.String(128), nullable=False),
            sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("captured_by", sa.String(128), nullable=False),
            sa.Column("summary", sa.Text(), server_default=""),
            sa.Column("redacted", sa.Boolean(), server_default=sa.false()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
    cols = [c["name"] for c in insp.get_columns("browser_sessions")]
    if "debug_enabled" not in cols:
        op.add_column(
            "browser_sessions",
            sa.Column("debug_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        )
    if "latest_artifact_summary" not in cols:
        op.add_column(
            "browser_sessions",
            sa.Column("latest_artifact_summary", sa.Text(), server_default="", nullable=False),
        )


def downgrade() -> None:
    op.drop_table("browser_debug_artifacts")
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("browser_sessions")]
    if "latest_artifact_summary" in cols:
        op.drop_column("browser_sessions", "latest_artifact_summary")
    if "debug_enabled" in cols:
        op.drop_column("browser_sessions", "debug_enabled")