"""Data exchange package table"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_data_exchange_package"
down_revision = "0004_sanitary_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_exchange_package",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("direction", sa.String(), sa.CheckConstraint("direction in ('export','import')")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("package_format", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("notes", sa.Text()),
    )
    op.create_index(
        "ix_data_exchange_package_direction_created_at",
        "data_exchange_package",
        ["direction", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_data_exchange_package_direction_created_at", table_name="data_exchange_package")
    op.drop_table("data_exchange_package")
