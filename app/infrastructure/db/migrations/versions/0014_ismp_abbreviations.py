from __future__ import annotations

from contextlib import suppress

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0014_ismp_abbreviations"
down_revision = "0013_ismp_case"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ref_ismp_abbreviations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )

    allowed = "('ВАП','КА-ИК','КА-ИМП','ИОХВ','ПАП','БАК','СЕПСИС')"
    with op.batch_alter_table("ismp_case") as batch:
        with suppress(Exception):
            batch.drop_constraint("ck_ismp_case_ismp_type", type_="check")
        batch.create_check_constraint("ck_ismp_case_ismp_type", f"ismp_type in {allowed}")


def downgrade() -> None:
    allowed = "('ВАП','КА-ИК','КА-ИМП')"
    with op.batch_alter_table("ismp_case") as batch:
        with suppress(Exception):
            batch.drop_constraint("ck_ismp_case_ismp_type", type_="check")
        batch.create_check_constraint("ck_ismp_case_ismp_type", f"ismp_type in {allowed}")

    op.drop_table("ref_ismp_abbreviations")
