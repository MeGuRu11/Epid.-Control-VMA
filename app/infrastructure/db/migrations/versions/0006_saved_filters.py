"""Saved filters table"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_saved_filters"
down_revision = "0005_data_exchange_package"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_filters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filter_type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.UniqueConstraint("filter_type", "name", name="uq_saved_filters_type_name"),
    )
    op.create_index(
        "ix_saved_filters_type_created_at",
        "saved_filters",
        ["filter_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_saved_filters_type_created_at", table_name="saved_filters")
    op.drop_table("saved_filters")
