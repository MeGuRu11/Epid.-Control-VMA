from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0013_ismp_case"
down_revision = "0012_lab_qc_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ismp_case",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("emr_case_id", sa.Integer(), sa.ForeignKey("emr_case.id"), nullable=False),
        sa.Column("ismp_type", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("ismp_type in ('\u0412\u0410\u041f','\u041a\u0410-\u0418\u041a','\u041a\u0410-\u0418\u041c\u041f','\u0418\u041e\u0425\u0412','\u041f\u0410\u041f','\u0411\u0410\u041a','\u0421\u0415\u041f\u0421\u0418\u0421')", name="ck_ismp_case_ismp_type"),
    )
    op.create_index("ix_ismp_case_emr_case_id", "ismp_case", ["emr_case_id"])
    op.create_index("ix_ismp_case_start_date", "ismp_case", ["start_date"])


def downgrade() -> None:
    op.drop_index("ix_ismp_case_start_date", table_name="ismp_case")
    op.drop_index("ix_ismp_case_emr_case_id", table_name="ismp_case")
    op.drop_table("ismp_case")
