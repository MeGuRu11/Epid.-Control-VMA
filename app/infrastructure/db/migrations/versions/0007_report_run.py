"""Report run table"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_report_run"
down_revision = "0006_saved_filters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("report_type", sa.String(), nullable=False),
        sa.Column("filters_json", sa.Text(), nullable=False),
        sa.Column("result_summary_json", sa.Text(), nullable=False),
        sa.Column("artifact_path", sa.String()),
        sa.Column("artifact_sha256", sa.String()),
    )
    op.create_index("ix_report_run_created_at", "report_run", ["created_at"], unique=False)
    op.create_index(
        "ix_report_run_report_type_created_at",
        "report_run",
        ["report_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_report_run_report_type_created_at", table_name="report_run")
    op.drop_index("ix_report_run_created_at", table_name="report_run")
    op.drop_table("report_run")
