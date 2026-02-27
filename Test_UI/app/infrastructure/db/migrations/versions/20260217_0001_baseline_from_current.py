"""baseline_from_current

Revision ID: 20260217_0001
Revises:
Create Date: 2026-02-17
"""

from __future__ import annotations

from alembic import op

from app.infrastructure.db.models_sqlalchemy import Base

revision = "20260217_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

