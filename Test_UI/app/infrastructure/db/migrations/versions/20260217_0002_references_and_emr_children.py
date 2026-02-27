"""references_and_emr_children

Revision ID: 20260217_0002
Revises: 20260217_0001
Create Date: 2026-02-17
"""

from __future__ import annotations

from alembic import op

revision = "20260217_0002"
down_revision = "20260217_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_ref_icd10_title ON ref_icd10(title)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ref_microorganisms_name ON ref_microorganisms(name)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ref_microorganisms_group ON ref_microorganisms(taxon_group)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ref_antibiotics_group ON ref_antibiotics(group_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_emr_case_department_id ON emr_case(department_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_emr_case_hospital_case_no ON emr_case(hospital_case_no)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_emr_case_version_current ON emr_case_version(emr_case_id, is_current)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_emr_diagnosis_code ON emr_diagnosis(icd10_code)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_emr_intervention_type_start ON emr_intervention(type, start_dt)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_emr_abx_course_antibiotic_start ON emr_antibiotic_course(antibiotic_id, start_dt)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ref_icd10_title")
    op.execute("DROP INDEX IF EXISTS ix_ref_microorganisms_name")
    op.execute("DROP INDEX IF EXISTS ix_ref_microorganisms_group")
    op.execute("DROP INDEX IF EXISTS ix_ref_antibiotics_group")
    op.execute("DROP INDEX IF EXISTS ix_emr_case_department_id")
    op.execute("DROP INDEX IF EXISTS ix_emr_case_hospital_case_no")
    op.execute("DROP INDEX IF EXISTS ix_emr_case_version_current")
    op.execute("DROP INDEX IF EXISTS ix_emr_diagnosis_code")
    op.execute("DROP INDEX IF EXISTS ix_emr_intervention_type_start")
    op.execute("DROP INDEX IF EXISTS ix_emr_abx_course_antibiotic_start")

