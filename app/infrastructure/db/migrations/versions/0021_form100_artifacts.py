"""Add Form100 signed version and artifact history.

Revision ID: 0021_form100_artifacts
Revises: 2daa0dea652d
Create Date: 2026-05-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0021_form100_artifacts"
down_revision = "2daa0dea652d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("form100", schema=None) as batch_op:
        batch_op.add_column(sa.Column("signed_version", sa.Integer(), nullable=True))

    op.execute("UPDATE form100 SET signed_version = version WHERE status = 'SIGNED'")

    op.create_table(
        "form100_artifact",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("form100_id", sa.String(length=36), nullable=False),
        sa.Column("version_at_generation", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("generated_by", sa.String(), nullable=True),
        sa.CheckConstraint("kind in ('pdf','json','zip')", name="ck_form100_artifact_kind"),
        sa.ForeignKeyConstraint(["form100_id"], ["form100.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_form100_artifact_form100_id", "form100_artifact", ["form100_id"])
    op.create_index("ix_form100_artifact_generated_at", "form100_artifact", ["generated_at"])
    op.create_index("ix_form100_artifact_form100_kind", "form100_artifact", ["form100_id", "kind"])


def downgrade() -> None:
    op.drop_index("ix_form100_artifact_form100_kind", table_name="form100_artifact")
    op.drop_index("ix_form100_artifact_generated_at", table_name="form100_artifact")
    op.drop_index("ix_form100_artifact_form100_id", table_name="form100_artifact")
    op.drop_table("form100_artifact")

    with op.batch_alter_table("form100", schema=None) as batch_op:
        batch_op.drop_column("signed_version")
