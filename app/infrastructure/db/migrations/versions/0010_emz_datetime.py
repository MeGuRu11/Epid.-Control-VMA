"""emz dates to datetime

Revision ID: 0010_emz_datetime
Revises: 0009_perf_indexes
Create Date: 2026-01-15 10:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0010_emz_datetime"
down_revision = "0009_perf_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("emr_case_version") as batch:
        batch.alter_column("admission_date", type_=sa.DateTime(), existing_type=sa.Date())
        batch.alter_column("injury_date", type_=sa.DateTime(), existing_type=sa.Date())
        batch.alter_column("outcome_date", type_=sa.DateTime(), existing_type=sa.Date())


def downgrade() -> None:
    with op.batch_alter_table("emr_case_version") as batch:
        batch.alter_column("admission_date", type_=sa.Date(), existing_type=sa.DateTime())
        batch.alter_column("injury_date", type_=sa.Date(), existing_type=sa.DateTime())
        batch.alter_column("outcome_date", type_=sa.Date(), existing_type=sa.DateTime())
