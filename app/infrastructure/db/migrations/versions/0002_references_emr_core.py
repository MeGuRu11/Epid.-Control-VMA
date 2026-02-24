"""References and EMR core tables"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_references_emr_core"
down_revision = "0001_initial_users_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
    )

    op.create_table(
        "ref_icd10",
        sa.Column("code", sa.String(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )

    op.create_table(
        "ref_microorganisms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(), unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("taxon_group", sa.String()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )

    op.create_table(
        "ref_antibiotic_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(), unique=True),
        sa.Column("name", sa.String(), nullable=False),
    )

    op.create_table(
        "ref_antibiotics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(), unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("ref_antibiotic_groups.id")),
    )

    op.create_table(
        "ref_phages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(), unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )

    op.create_table(
        "ref_material_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(), unique=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
    )

    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("dob", sa.Date()),
        sa.Column("sex", sa.String(), sa.CheckConstraint("sex in ('M','F','U')"), server_default=sa.literal("U")),
        sa.Column("category", sa.String()),
        sa.Column("military_unit", sa.String()),
        sa.Column("military_district", sa.String()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index("ix_patients_full_name", "patients", ["full_name"], unique=False)
    op.create_index("ix_patients_dob", "patients", ["dob"], unique=False)
    op.create_index("ix_patients_sex", "patients", ["sex"], unique=False)

    op.create_table(
        "emr_case",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("hospital_case_no", sa.String(), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.UniqueConstraint("patient_id", "hospital_case_no", name="uq_emr_case_patient_case"),
    )
    op.create_index("ix_emr_case_department_id", "emr_case", ["department_id"], unique=False)
    op.create_index("ix_emr_case_hospital_case_no", "emr_case", ["hospital_case_no"], unique=False)

    op.create_table(
        "emr_case_version",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("emr_case_id", sa.Integer(), sa.ForeignKey("emr_case.id"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_to", sa.DateTime()),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("entered_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("admission_date", sa.Date()),
        sa.Column("injury_date", sa.Date()),
        sa.Column("outcome_date", sa.Date()),
        sa.Column("outcome_type", sa.String()),
        sa.Column("severity", sa.String()),
        sa.Column("vph_sp_score", sa.Integer()),
        sa.Column("vph_p_or_score", sa.Integer()),
        sa.Column("sofa_score", sa.Integer()),
        sa.Column("days_to_admission", sa.Integer()),
        sa.Column("length_of_stay_days", sa.Integer()),
        sa.UniqueConstraint("emr_case_id", "version_no", name="uq_emr_case_version_no"),
    )
    op.create_index("ix_emr_case_version_emr_case_id_is_current", "emr_case_version", ["emr_case_id", "is_current"], unique=False)
    op.create_index("ix_emr_case_version_admission_date", "emr_case_version", ["admission_date"], unique=False)
    op.create_index("ix_emr_case_version_outcome_date", "emr_case_version", ["outcome_date"], unique=False)
    op.create_index("ix_emr_case_version_severity", "emr_case_version", ["severity"], unique=False)
    op.create_index("ix_emr_case_version_sofa_score", "emr_case_version", ["sofa_score"], unique=False)

    op.create_table(
        "emr_diagnosis",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("emr_case_version_id", sa.Integer(), sa.ForeignKey("emr_case_version.id"), nullable=False),
        sa.Column("kind", sa.String(), sa.CheckConstraint("kind in ('admission','discharge','complication')")),
        sa.Column("icd10_code", sa.String(), sa.ForeignKey("ref_icd10.code")),
        sa.Column("free_text", sa.Text()),
    )
    op.create_index("ix_emr_diagnosis_emr_case_version_id", "emr_diagnosis", ["emr_case_version_id"], unique=False)
    op.create_index("ix_emr_diagnosis_icd10_code", "emr_diagnosis", ["icd10_code"], unique=False)
    op.create_index("ix_emr_diagnosis_kind_icd10_code", "emr_diagnosis", ["kind", "icd10_code"], unique=False)

    op.create_table(
        "emr_intervention",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("emr_case_version_id", sa.Integer(), sa.ForeignKey("emr_case_version.id"), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("start_dt", sa.DateTime()),
        sa.Column("end_dt", sa.DateTime()),
        sa.Column("duration_minutes", sa.Integer()),
        sa.Column("performed_by", sa.String()),
        sa.Column("notes", sa.Text()),
    )
    op.create_index("ix_emr_intervention_emr_case_version_id_type", "emr_intervention", ["emr_case_version_id", "type"], unique=False)
    op.create_index("ix_emr_intervention_type_start_dt", "emr_intervention", ["type", "start_dt"], unique=False)

    op.create_table(
        "emr_antibiotic_course",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("emr_case_version_id", sa.Integer(), sa.ForeignKey("emr_case_version.id"), nullable=False),
        sa.Column("start_dt", sa.DateTime()),
        sa.Column("end_dt", sa.DateTime()),
        sa.Column("antibiotic_id", sa.Integer(), sa.ForeignKey("ref_antibiotics.id")),
        sa.Column("drug_name_free", sa.Text()),
        sa.Column("route", sa.String()),
        sa.Column("dose", sa.String()),
    )
    op.create_index("ix_emr_antibiotic_course_emr_case_version_id", "emr_antibiotic_course", ["emr_case_version_id"], unique=False)
    op.create_index("ix_emr_antibiotic_course_antibiotic_id", "emr_antibiotic_course", ["antibiotic_id"], unique=False)
    op.create_index("ix_emr_antibiotic_course_start_dt", "emr_antibiotic_course", ["start_dt"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_emr_antibiotic_course_start_dt", table_name="emr_antibiotic_course")
    op.drop_index("ix_emr_antibiotic_course_antibiotic_id", table_name="emr_antibiotic_course")
    op.drop_index("ix_emr_antibiotic_course_emr_case_version_id", table_name="emr_antibiotic_course")
    op.drop_table("emr_antibiotic_course")

    op.drop_index("ix_emr_intervention_type_start_dt", table_name="emr_intervention")
    op.drop_index("ix_emr_intervention_emr_case_version_id_type", table_name="emr_intervention")
    op.drop_table("emr_intervention")

    op.drop_index("ix_emr_diagnosis_kind_icd10_code", table_name="emr_diagnosis")
    op.drop_index("ix_emr_diagnosis_icd10_code", table_name="emr_diagnosis")
    op.drop_index("ix_emr_diagnosis_emr_case_version_id", table_name="emr_diagnosis")
    op.drop_table("emr_diagnosis")

    op.drop_index("ix_emr_case_version_sofa_score", table_name="emr_case_version")
    op.drop_index("ix_emr_case_version_severity", table_name="emr_case_version")
    op.drop_index("ix_emr_case_version_outcome_date", table_name="emr_case_version")
    op.drop_index("ix_emr_case_version_admission_date", table_name="emr_case_version")
    op.drop_index("ix_emr_case_version_emr_case_id_is_current", table_name="emr_case_version")
    op.drop_table("emr_case_version")

    op.drop_index("ix_emr_case_hospital_case_no", table_name="emr_case")
    op.drop_index("ix_emr_case_department_id", table_name="emr_case")
    op.drop_table("emr_case")

    op.drop_index("ix_patients_sex", table_name="patients")
    op.drop_index("ix_patients_dob", table_name="patients")
    op.drop_index("ix_patients_full_name", table_name="patients")
    op.drop_table("patients")

    op.drop_table("ref_material_types")
    op.drop_table("ref_phages")
    op.drop_table("ref_antibiotics")
    op.drop_table("ref_antibiotic_groups")
    op.drop_table("ref_microorganisms")
    op.drop_table("ref_icd10")
    op.drop_table("departments")
