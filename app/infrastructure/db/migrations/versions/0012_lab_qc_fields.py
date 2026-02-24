"""Lab QC fields.

Revision ID: 0012_lab_qc_fields
Revises: 0011_merge_heads
Create Date: 2026-02-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0012_lab_qc_fields"
down_revision = "0011_merge_heads"
branch_labels = None
depends_on = None


def _get_existing_columns(conn) -> set[str]:
    rows = conn.exec_driver_sql("PRAGMA table_info('lab_sample')").fetchall()
    return {row[1] for row in rows}


def _constraint_exists(conn, name: str) -> bool:
    row = conn.exec_driver_sql(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='lab_sample'"
    ).fetchone()
    if not row or not row[0]:
        return False
    return name in row[0]


def upgrade() -> None:
    conn = op.get_bind()
    existing_cols = _get_existing_columns(conn)
    has_constraint = _constraint_exists(conn, "ck_lab_sample_qc_status")
    with op.batch_alter_table("lab_sample") as batch:
        if "qc_due_at" not in existing_cols:
            batch.add_column(sa.Column("qc_due_at", sa.DateTime()))
        if "qc_status" not in existing_cols:
            batch.add_column(sa.Column("qc_status", sa.String()))
        if not has_constraint:
            batch.create_check_constraint(
                "ck_lab_sample_qc_status",
                "qc_status in ('valid','conditional','rejected')",
            )


def downgrade() -> None:
    conn = op.get_bind()
    existing_cols = _get_existing_columns(conn)
    has_constraint = _constraint_exists(conn, "ck_lab_sample_qc_status")
    with op.batch_alter_table("lab_sample") as batch:
        if has_constraint:
            batch.drop_constraint("ck_lab_sample_qc_status", type_="check")
        if "qc_status" in existing_cols:
            batch.drop_column("qc_status")
        if "qc_due_at" in existing_cols:
            batch.drop_column("qc_due_at")
