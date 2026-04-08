"""Add persistent login lockout fields to users.

Revision ID: 0020_login_lockout_fields
Revises: 0019_form100_v2_schema
Create Date: 2026-04-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0020_login_lockout_fields"
down_revision = "0019_form100_v2_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "failed_login_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.add_column(sa.Column("locked_until", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("locked_until")
        batch_op.drop_column("failed_login_count")
