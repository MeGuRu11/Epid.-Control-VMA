"""feat: fk ondelete policies.

Revision ID: 2daa0dea652d
Revises: 0020_login_lockout_fields
Create Date: 2026-04-08
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "2daa0dea652d"
down_revision = "0020_login_lockout_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("emr_case", schema=None) as batch_op:
        batch_op.drop_constraint("fk_emr_case_patient_id_patients", type_="foreignkey")
        batch_op.create_foreign_key(
            op.f("fk_emr_case_patient_id_patients"),
            "patients",
            ["patient_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("lab_microbe_isolation", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_lab_microbe_isolation_microorganism_id_ref_microorganisms",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            op.f("fk_lab_microbe_isolation_microorganism_id_ref_microorganisms"),
            "ref_microorganisms",
            ["microorganism_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("lab_sample", schema=None) as batch_op:
        batch_op.drop_constraint("fk_lab_sample_patient_id_patients", type_="foreignkey")
        batch_op.create_foreign_key(
            op.f("fk_lab_sample_patient_id_patients"),
            "patients",
            ["patient_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("lab_sample", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("fk_lab_sample_patient_id_patients"), type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_lab_sample_patient_id_patients",
            "patients",
            ["patient_id"],
            ["id"],
        )

    with op.batch_alter_table("lab_microbe_isolation", schema=None) as batch_op:
        batch_op.drop_constraint(
            op.f("fk_lab_microbe_isolation_microorganism_id_ref_microorganisms"),
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_lab_microbe_isolation_microorganism_id_ref_microorganisms",
            "ref_microorganisms",
            ["microorganism_id"],
            ["id"],
        )

    with op.batch_alter_table("emr_case", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("fk_emr_case_patient_id_patients"), type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_emr_case_patient_id_patients",
            "patients",
            ["patient_id"],
            ["id"],
        )
