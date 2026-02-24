from __future__ import annotations

from contextlib import suppress

from alembic import op

# revision identifiers, used by Alembic.
revision = "0015_fix_ismp_types"
down_revision = "0014_ismp_abbreviations"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
