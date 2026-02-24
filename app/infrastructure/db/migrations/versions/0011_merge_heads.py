"""Merge heads: sanitary sequence + emz datetime.

Revision ID: 0011_merge_heads
Revises: 0006_sanitary_number_sequence, 0010_emz_datetime
Create Date: 2026-01-15
"""

from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "0011_merge_heads"
down_revision = ("0006_sanitary_number_sequence", "0010_emz_datetime")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision.
    pass


def downgrade() -> None:
    # Merge-only revision.
    pass
