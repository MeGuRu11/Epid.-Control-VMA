"""Add composite indexes for analytics filters.

Revision ID: 0017_analytics_filter_indexes
Revises: 0016_fk_cascade
Create Date: 2026-02-13
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0017_analytics_filter_indexes"
down_revision = "0016_fk_cascade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_patients_category", "patients", ["category"], unique=False)
    op.create_index(
        "ix_lab_sample_emr_case_id_taken_at",
        "lab_sample",
        ["emr_case_id", "taken_at"],
        unique=False,
    )
    op.create_index(
        "ix_lab_sample_growth_flag_taken_at",
        "lab_sample",
        ["growth_flag", "taken_at"],
        unique=False,
    )
    op.create_index(
        "ix_lab_microbe_isolation_microorganism_id_lab_sample_id",
        "lab_microbe_isolation",
        ["microorganism_id", "lab_sample_id"],
        unique=False,
    )
    op.create_index(
        "ix_lab_abx_susceptibility_antibiotic_id_lab_sample_id",
        "lab_abx_susceptibility",
        ["antibiotic_id", "lab_sample_id"],
        unique=False,
    )
    op.create_index(
        "ix_emr_case_version_is_current_admission_date_emr_case_id",
        "emr_case_version",
        ["is_current", "admission_date", "emr_case_id"],
        unique=False,
    )
    op.create_index(
        "ix_emr_diagnosis_icd10_code_emr_case_version_id",
        "emr_diagnosis",
        ["icd10_code", "emr_case_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_ismp_case_start_date_emr_case_id_ismp_type",
        "ismp_case",
        ["start_date", "emr_case_id", "ismp_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ismp_case_start_date_emr_case_id_ismp_type", table_name="ismp_case")
    op.drop_index("ix_emr_diagnosis_icd10_code_emr_case_version_id", table_name="emr_diagnosis")
    op.drop_index(
        "ix_emr_case_version_is_current_admission_date_emr_case_id",
        table_name="emr_case_version",
    )
    op.drop_index(
        "ix_lab_abx_susceptibility_antibiotic_id_lab_sample_id",
        table_name="lab_abx_susceptibility",
    )
    op.drop_index(
        "ix_lab_microbe_isolation_microorganism_id_lab_sample_id",
        table_name="lab_microbe_isolation",
    )
    op.drop_index("ix_lab_sample_growth_flag_taken_at", table_name="lab_sample")
    op.drop_index("ix_lab_sample_emr_case_id_taken_at", table_name="lab_sample")
    op.drop_index("ix_patients_category", table_name="patients")
