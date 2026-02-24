"""add performance indexes for analytics

Revision ID: 0009_perf_indexes
Revises: 0008_fts5_search
Create Date: 2025-12-30 12:20:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0009_perf_indexes"
down_revision = "0008_fts5_search"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_lab_sample_taken_at", "lab_sample", ["taken_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lab_sample_taken_at", table_name="lab_sample")
