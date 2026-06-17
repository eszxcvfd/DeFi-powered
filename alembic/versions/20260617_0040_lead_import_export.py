"""Lead CSV import/export baseline (US-050) —
durable `lead_import_jobs` and
`lead_import_rows` tables. The migration
is additive; the documented rollback path
is to drop the new tables. No existing rows
are touched.

Revision ID: 20260617_0040
Revises: 20260616_0039
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260617_0040"
down_revision: str | Sequence[str] | None = "20260616_0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table_name in set(insp.get_table_names())


def upgrade() -> None:
    if not _has_table("lead_import_jobs"):
        op.create_table(
            "lead_import_jobs",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "organization_id", sa.String(length=36), nullable=False
            ),
            sa.Column(
                "created_by_user_id",
                sa.String(length=128),
                nullable=False,
                server_default="system",
            ),
            sa.Column(
                "actor_role",
                sa.String(length=32),
                nullable=False,
                server_default="viewer",
            ),
            sa.Column("filename", sa.String(length=300), nullable=False),
            sa.Column("file_sha256", sa.String(length=64), nullable=False),
            sa.Column("delimiter", sa.String(length=4), nullable=False),
            sa.Column("mapping_json", sa.Text(), nullable=False),
            sa.Column("provenance_note", sa.Text(), nullable=False),
            sa.Column(
                "campaign_id", sa.String(length=36), nullable=True
            ),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ready_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "duplicate_rows", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column("invalid_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("skipped_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "applied_at", sa.DateTime(timezone=True), nullable=True
            ),
        )
        op.create_index(
            "ix_lead_import_jobs_org",
            "lead_import_jobs",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            "ix_lead_import_jobs_org_created",
            "lead_import_jobs",
            ["organization_id", "created_at"],
            unique=False,
        )
        op.create_index(
            "ix_lead_import_jobs_org_status",
            "lead_import_jobs",
            ["organization_id", "status"],
            unique=False,
        )

    if not _has_table("lead_import_rows"):
        op.create_table(
            "lead_import_rows",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("import_job_id", sa.String(length=36), nullable=False),
            sa.Column(
                "organization_id", sa.String(length=36), nullable=False
            ),
            sa.Column("row_number", sa.Integer(), nullable=False),
            sa.Column(
                "normalized_payload_json", sa.Text(), nullable=False
            ),
            sa.Column(
                "classification",
                sa.String(length=32),
                nullable=False,
                server_default="invalid",
            ),
            sa.Column(
                "duplicate_lead_id", sa.String(length=36), nullable=True
            ),
            sa.Column(
                "duplicate_reason", sa.String(length=200), nullable=True
            ),
            sa.Column("error_codes_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_lead_id", sa.String(length=36), nullable=True),
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
            "ix_lead_import_rows_job",
            "lead_import_rows",
            ["import_job_id"],
            unique=False,
        )
        op.create_index(
            "ix_lead_import_rows_job_classification",
            "lead_import_rows",
            ["import_job_id", "classification", "row_number"],
            unique=False,
        )
        op.create_index(
            "ix_lead_import_rows_org_duplicate",
            "lead_import_rows",
            ["organization_id", "duplicate_lead_id"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("lead_import_rows"):
        op.drop_table("lead_import_rows")
    if _has_table("lead_import_jobs"):
        op.drop_table("lead_import_jobs")
