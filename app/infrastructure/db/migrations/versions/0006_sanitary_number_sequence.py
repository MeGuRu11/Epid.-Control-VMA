"""Add sanitary number sequence table.

Revision ID: 0006_sanitary_number_sequence
Revises: 0005_data_exchange_package
Create Date: 2026-01-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_sanitary_number_sequence"
down_revision = "0005_data_exchange_package"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sanitary_number_sequence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seq_date", sa.Date(), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False),
        sa.UniqueConstraint("seq_date", name="uq_sanitary_number_sequence"),
    )


def downgrade() -> None:
    op.drop_table("sanitary_number_sequence")
