"""Add ON DELETE CASCADE to detail foreign keys.

Revision ID: 0016_fk_cascade
Revises: 0015_fix_ismp_types
Create Date: 2026-02-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0016_fk_cascade"
down_revision = "0015_fix_ismp_types"
branch_labels = None
depends_on = None


def _recreate_table(table_name: str, columns: list[str], create_table, create_indexes) -> None:
    temp_name = f"{table_name}__old"
    op.rename_table(table_name, temp_name)
    create_table()
    cols_csv = ", ".join(columns)
    op.execute(f"INSERT INTO {table_name} ({cols_csv}) SELECT {cols_csv} FROM {temp_name}")
    op.drop_table(temp_name)
    for create_index in create_indexes:
        create_index()


def _create_emr_case_version(ondelete: str | None) -> None:
    op.create_table(
        "emr_case_version",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("emr_case_id", sa.Integer(), sa.ForeignKey("emr_case.id", ondelete=ondelete), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_to", sa.DateTime()),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("entered_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("admission_date", sa.DateTime()),
        sa.Column("injury_date", sa.DateTime()),
        sa.Column("outcome_date", sa.DateTime()),
        sa.Column("outcome_type", sa.String()),
        sa.Column("severity", sa.String()),
        sa.Column("vph_sp_score", sa.Integer()),
        sa.Column("vph_p_or_score", sa.Integer()),
        sa.Column("sofa_score", sa.Integer()),
        sa.Column("days_to_admission", sa.Integer()),
        sa.Column("length_of_stay_days", sa.Integer()),
        sa.UniqueConstraint("emr_case_id", "version_no", name="uq_emr_case_version_no"),
    )


def _create_emr_diagnosis(ondelete: str | None) -> None:
    op.create_table(
        "emr_diagnosis",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "emr_case_version_id",
            sa.Integer(),
            sa.ForeignKey("emr_case_version.id", ondelete=ondelete),
            nullable=False,
        ),
        sa.Column("kind", sa.String(), sa.CheckConstraint("kind in ('admission','discharge','complication')")),
        sa.Column("icd10_code", sa.String(), sa.ForeignKey("ref_icd10.code")),
        sa.Column("free_text", sa.Text()),
    )


def _create_emr_intervention(ondelete: str | None) -> None:
    op.create_table(
        "emr_intervention",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "emr_case_version_id",
            sa.Integer(),
            sa.ForeignKey("emr_case_version.id", ondelete=ondelete),
            nullable=False,
        ),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("start_dt", sa.DateTime()),
        sa.Column("end_dt", sa.DateTime()),
        sa.Column("duration_minutes", sa.Integer()),
        sa.Column("performed_by", sa.String()),
        sa.Column("notes", sa.Text()),
    )


def _create_emr_antibiotic_course(ondelete: str | None) -> None:
    op.create_table(
        "emr_antibiotic_course",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "emr_case_version_id",
            sa.Integer(),
            sa.ForeignKey("emr_case_version.id", ondelete=ondelete),
            nullable=False,
        ),
        sa.Column("start_dt", sa.DateTime()),
        sa.Column("end_dt", sa.DateTime()),
        sa.Column("antibiotic_id", sa.Integer(), sa.ForeignKey("ref_antibiotics.id")),
        sa.Column("drug_name_free", sa.Text()),
        sa.Column("route", sa.String()),
        sa.Column("dose", sa.String()),
    )


def _create_ismp_case(ondelete: str | None) -> None:
    op.create_table(
        "ismp_case",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("emr_case_id", sa.Integer(), sa.ForeignKey("emr_case.id", ondelete=ondelete), nullable=False),
        sa.Column("ismp_type", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "ismp_type in ('\u0412\u0410\u041f','\u041a\u0410-\u0418\u041a','\u041a\u0410-\u0418\u041c\u041f','\u0418\u041e\u0425\u0412','\u041f\u0410\u041f','\u0411\u0410\u041a','\u0421\u0415\u041f\u0421\u0418\u0421')",
            name="ck_ismp_case_ismp_type",
        ),
    )


def _create_lab_microbe_isolation(ondelete: str | None) -> None:
    op.create_table(
        "lab_microbe_isolation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lab_sample_id", sa.Integer(), sa.ForeignKey("lab_sample.id", ondelete=ondelete), nullable=False),
        sa.Column("microorganism_id", sa.Integer(), sa.ForeignKey("ref_microorganisms.id")),
        sa.Column("microorganism_free", sa.Text()),
        sa.Column("notes", sa.Text()),
    )


def _create_lab_abx_susceptibility(ondelete: str | None) -> None:
    op.create_table(
        "lab_abx_susceptibility",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lab_sample_id", sa.Integer(), sa.ForeignKey("lab_sample.id", ondelete=ondelete), nullable=False),
        sa.Column("antibiotic_id", sa.Integer(), sa.ForeignKey("ref_antibiotics.id"), nullable=False),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("ref_antibiotic_groups.id")),
        sa.Column("ris", sa.String(), sa.CheckConstraint("ris in ('R','I','S')")),
        sa.Column("mic_mg_l", sa.Integer()),
        sa.Column("method", sa.String()),
    )


def _create_lab_phage_panel_result(ondelete: str | None) -> None:
    op.create_table(
        "lab_phage_panel_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lab_sample_id", sa.Integer(), sa.ForeignKey("lab_sample.id", ondelete=ondelete), nullable=False),
        sa.Column("phage_id", sa.Integer(), sa.ForeignKey("ref_phages.id")),
        sa.Column("phage_free", sa.Text()),
        sa.Column("lysis_diameter_mm", sa.Integer()),
    )


def _create_san_microbe_isolation(ondelete: str | None) -> None:
    op.create_table(
        "san_microbe_isolation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sanitary_sample_id",
            sa.Integer(),
            sa.ForeignKey("sanitary_sample.id", ondelete=ondelete),
            nullable=False,
        ),
        sa.Column("microorganism_id", sa.Integer(), sa.ForeignKey("ref_microorganisms.id")),
        sa.Column("microorganism_free", sa.Text()),
        sa.Column("notes", sa.Text()),
    )


def _create_san_abx_susceptibility(ondelete: str | None) -> None:
    op.create_table(
        "san_abx_susceptibility",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sanitary_sample_id",
            sa.Integer(),
            sa.ForeignKey("sanitary_sample.id", ondelete=ondelete),
            nullable=False,
        ),
        sa.Column("antibiotic_id", sa.Integer(), sa.ForeignKey("ref_antibiotics.id"), nullable=False),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("ref_antibiotic_groups.id")),
        sa.Column("ris", sa.String(), sa.CheckConstraint("ris in ('R','I','S')")),
        sa.Column("mic_mg_l", sa.Integer()),
        sa.Column("method", sa.String()),
    )


def _create_san_phage_panel_result(ondelete: str | None) -> None:
    op.create_table(
        "san_phage_panel_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sanitary_sample_id",
            sa.Integer(),
            sa.ForeignKey("sanitary_sample.id", ondelete=ondelete),
            nullable=False,
        ),
        sa.Column("phage_id", sa.Integer(), sa.ForeignKey("ref_phages.id")),
        sa.Column("phage_free", sa.Text()),
        sa.Column("lysis_diameter_mm", sa.Integer()),
    )


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "sqlite":
        return

    op.execute("PRAGMA foreign_keys=OFF")

    _recreate_table(
        "emr_case_version",
        [
            "id",
            "emr_case_id",
            "version_no",
            "valid_from",
            "valid_to",
            "is_current",
            "entered_by",
            "admission_date",
            "injury_date",
            "outcome_date",
            "outcome_type",
            "severity",
            "vph_sp_score",
            "vph_p_or_score",
            "sofa_score",
            "days_to_admission",
            "length_of_stay_days",
        ],
        lambda: _create_emr_case_version("CASCADE"),
        [
            lambda: op.create_index(
                "ix_emr_case_version_emr_case_id_is_current",
                "emr_case_version",
                ["emr_case_id", "is_current"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_case_version_admission_date",
                "emr_case_version",
                ["admission_date"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_case_version_outcome_date",
                "emr_case_version",
                ["outcome_date"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_case_version_severity",
                "emr_case_version",
                ["severity"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_case_version_sofa_score",
                "emr_case_version",
                ["sofa_score"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "emr_diagnosis",
        ["id", "emr_case_version_id", "kind", "icd10_code", "free_text"],
        lambda: _create_emr_diagnosis("CASCADE"),
        [
            lambda: op.create_index(
                "ix_emr_diagnosis_emr_case_version_id",
                "emr_diagnosis",
                ["emr_case_version_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_diagnosis_icd10_code",
                "emr_diagnosis",
                ["icd10_code"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_diagnosis_kind_icd10_code",
                "emr_diagnosis",
                ["kind", "icd10_code"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "emr_intervention",
        ["id", "emr_case_version_id", "type", "start_dt", "end_dt", "duration_minutes", "performed_by", "notes"],
        lambda: _create_emr_intervention("CASCADE"),
        [
            lambda: op.create_index(
                "ix_emr_intervention_emr_case_version_id_type",
                "emr_intervention",
                ["emr_case_version_id", "type"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_intervention_type_start_dt",
                "emr_intervention",
                ["type", "start_dt"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "emr_antibiotic_course",
        ["id", "emr_case_version_id", "start_dt", "end_dt", "antibiotic_id", "drug_name_free", "route", "dose"],
        lambda: _create_emr_antibiotic_course("CASCADE"),
        [
            lambda: op.create_index(
                "ix_emr_antibiotic_course_emr_case_version_id",
                "emr_antibiotic_course",
                ["emr_case_version_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_antibiotic_course_antibiotic_id",
                "emr_antibiotic_course",
                ["antibiotic_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_antibiotic_course_start_dt",
                "emr_antibiotic_course",
                ["start_dt"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "ismp_case",
        ["id", "emr_case_id", "ismp_type", "start_date", "created_at"],
        lambda: _create_ismp_case("CASCADE"),
        [
            lambda: op.create_index("ix_ismp_case_emr_case_id", "ismp_case", ["emr_case_id"]),
            lambda: op.create_index("ix_ismp_case_start_date", "ismp_case", ["start_date"]),
        ],
    )

    _recreate_table(
        "lab_microbe_isolation",
        ["id", "lab_sample_id", "microorganism_id", "microorganism_free", "notes"],
        lambda: _create_lab_microbe_isolation("CASCADE"),
        [
            lambda: op.create_index(
                "ix_lab_microbe_isolation_lab_sample_id",
                "lab_microbe_isolation",
                ["lab_sample_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_lab_microbe_isolation_microorganism_id",
                "lab_microbe_isolation",
                ["microorganism_id"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "lab_abx_susceptibility",
        ["id", "lab_sample_id", "antibiotic_id", "group_id", "ris", "mic_mg_l", "method"],
        lambda: _create_lab_abx_susceptibility("CASCADE"),
        [
            lambda: op.create_index(
                "ix_lab_abx_susceptibility_lab_sample_id",
                "lab_abx_susceptibility",
                ["lab_sample_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_lab_abx_susceptibility_antibiotic_id_ris",
                "lab_abx_susceptibility",
                ["antibiotic_id", "ris"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_lab_abx_susceptibility_group_id_ris",
                "lab_abx_susceptibility",
                ["group_id", "ris"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "lab_phage_panel_result",
        ["id", "lab_sample_id", "phage_id", "phage_free", "lysis_diameter_mm"],
        lambda: _create_lab_phage_panel_result("CASCADE"),
        [
            lambda: op.create_index(
                "ix_lab_phage_panel_result_lab_sample_id",
                "lab_phage_panel_result",
                ["lab_sample_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_lab_phage_panel_result_phage_id",
                "lab_phage_panel_result",
                ["phage_id"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "san_microbe_isolation",
        ["id", "sanitary_sample_id", "microorganism_id", "microorganism_free", "notes"],
        lambda: _create_san_microbe_isolation("CASCADE"),
        [
            lambda: op.create_index(
                "ix_san_microbe_isolation_sanitary_sample_id",
                "san_microbe_isolation",
                ["sanitary_sample_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_san_microbe_isolation_microorganism_id",
                "san_microbe_isolation",
                ["microorganism_id"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "san_abx_susceptibility",
        ["id", "sanitary_sample_id", "antibiotic_id", "group_id", "ris", "mic_mg_l", "method"],
        lambda: _create_san_abx_susceptibility("CASCADE"),
        [
            lambda: op.create_index(
                "ix_san_abx_susceptibility_sanitary_sample_id",
                "san_abx_susceptibility",
                ["sanitary_sample_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_san_abx_susceptibility_antibiotic_id_ris",
                "san_abx_susceptibility",
                ["antibiotic_id", "ris"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_san_abx_susceptibility_group_id_ris",
                "san_abx_susceptibility",
                ["group_id", "ris"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "san_phage_panel_result",
        ["id", "sanitary_sample_id", "phage_id", "phage_free", "lysis_diameter_mm"],
        lambda: _create_san_phage_panel_result("CASCADE"),
        [
            lambda: op.create_index(
                "ix_san_phage_panel_result_sanitary_sample_id",
                "san_phage_panel_result",
                ["sanitary_sample_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_san_phage_panel_result_phage_id",
                "san_phage_panel_result",
                ["phage_id"],
                unique=False,
            ),
        ],
    )

    op.execute("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "sqlite":
        return

    op.execute("PRAGMA foreign_keys=OFF")

    _recreate_table(
        "emr_case_version",
        [
            "id",
            "emr_case_id",
            "version_no",
            "valid_from",
            "valid_to",
            "is_current",
            "entered_by",
            "admission_date",
            "injury_date",
            "outcome_date",
            "outcome_type",
            "severity",
            "vph_sp_score",
            "vph_p_or_score",
            "sofa_score",
            "days_to_admission",
            "length_of_stay_days",
        ],
        lambda: _create_emr_case_version(None),
        [
            lambda: op.create_index(
                "ix_emr_case_version_emr_case_id_is_current",
                "emr_case_version",
                ["emr_case_id", "is_current"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_case_version_admission_date",
                "emr_case_version",
                ["admission_date"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_case_version_outcome_date",
                "emr_case_version",
                ["outcome_date"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_case_version_severity",
                "emr_case_version",
                ["severity"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_case_version_sofa_score",
                "emr_case_version",
                ["sofa_score"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "emr_diagnosis",
        ["id", "emr_case_version_id", "kind", "icd10_code", "free_text"],
        lambda: _create_emr_diagnosis(None),
        [
            lambda: op.create_index(
                "ix_emr_diagnosis_emr_case_version_id",
                "emr_diagnosis",
                ["emr_case_version_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_diagnosis_icd10_code",
                "emr_diagnosis",
                ["icd10_code"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_diagnosis_kind_icd10_code",
                "emr_diagnosis",
                ["kind", "icd10_code"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "emr_intervention",
        ["id", "emr_case_version_id", "type", "start_dt", "end_dt", "duration_minutes", "performed_by", "notes"],
        lambda: _create_emr_intervention(None),
        [
            lambda: op.create_index(
                "ix_emr_intervention_emr_case_version_id_type",
                "emr_intervention",
                ["emr_case_version_id", "type"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_intervention_type_start_dt",
                "emr_intervention",
                ["type", "start_dt"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "emr_antibiotic_course",
        ["id", "emr_case_version_id", "start_dt", "end_dt", "antibiotic_id", "drug_name_free", "route", "dose"],
        lambda: _create_emr_antibiotic_course(None),
        [
            lambda: op.create_index(
                "ix_emr_antibiotic_course_emr_case_version_id",
                "emr_antibiotic_course",
                ["emr_case_version_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_antibiotic_course_antibiotic_id",
                "emr_antibiotic_course",
                ["antibiotic_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_emr_antibiotic_course_start_dt",
                "emr_antibiotic_course",
                ["start_dt"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "ismp_case",
        ["id", "emr_case_id", "ismp_type", "start_date", "created_at"],
        lambda: _create_ismp_case(None),
        [
            lambda: op.create_index("ix_ismp_case_emr_case_id", "ismp_case", ["emr_case_id"]),
            lambda: op.create_index("ix_ismp_case_start_date", "ismp_case", ["start_date"]),
        ],
    )

    _recreate_table(
        "lab_microbe_isolation",
        ["id", "lab_sample_id", "microorganism_id", "microorganism_free", "notes"],
        lambda: _create_lab_microbe_isolation(None),
        [
            lambda: op.create_index(
                "ix_lab_microbe_isolation_lab_sample_id",
                "lab_microbe_isolation",
                ["lab_sample_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_lab_microbe_isolation_microorganism_id",
                "lab_microbe_isolation",
                ["microorganism_id"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "lab_abx_susceptibility",
        ["id", "lab_sample_id", "antibiotic_id", "group_id", "ris", "mic_mg_l", "method"],
        lambda: _create_lab_abx_susceptibility(None),
        [
            lambda: op.create_index(
                "ix_lab_abx_susceptibility_lab_sample_id",
                "lab_abx_susceptibility",
                ["lab_sample_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_lab_abx_susceptibility_antibiotic_id_ris",
                "lab_abx_susceptibility",
                ["antibiotic_id", "ris"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_lab_abx_susceptibility_group_id_ris",
                "lab_abx_susceptibility",
                ["group_id", "ris"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "lab_phage_panel_result",
        ["id", "lab_sample_id", "phage_id", "phage_free", "lysis_diameter_mm"],
        lambda: _create_lab_phage_panel_result(None),
        [
            lambda: op.create_index(
                "ix_lab_phage_panel_result_lab_sample_id",
                "lab_phage_panel_result",
                ["lab_sample_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_lab_phage_panel_result_phage_id",
                "lab_phage_panel_result",
                ["phage_id"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "san_microbe_isolation",
        ["id", "sanitary_sample_id", "microorganism_id", "microorganism_free", "notes"],
        lambda: _create_san_microbe_isolation(None),
        [
            lambda: op.create_index(
                "ix_san_microbe_isolation_sanitary_sample_id",
                "san_microbe_isolation",
                ["sanitary_sample_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_san_microbe_isolation_microorganism_id",
                "san_microbe_isolation",
                ["microorganism_id"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "san_abx_susceptibility",
        ["id", "sanitary_sample_id", "antibiotic_id", "group_id", "ris", "mic_mg_l", "method"],
        lambda: _create_san_abx_susceptibility(None),
        [
            lambda: op.create_index(
                "ix_san_abx_susceptibility_sanitary_sample_id",
                "san_abx_susceptibility",
                ["sanitary_sample_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_san_abx_susceptibility_antibiotic_id_ris",
                "san_abx_susceptibility",
                ["antibiotic_id", "ris"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_san_abx_susceptibility_group_id_ris",
                "san_abx_susceptibility",
                ["group_id", "ris"],
                unique=False,
            ),
        ],
    )

    _recreate_table(
        "san_phage_panel_result",
        ["id", "sanitary_sample_id", "phage_id", "phage_free", "lysis_diameter_mm"],
        lambda: _create_san_phage_panel_result(None),
        [
            lambda: op.create_index(
                "ix_san_phage_panel_result_sanitary_sample_id",
                "san_phage_panel_result",
                ["sanitary_sample_id"],
                unique=False,
            ),
            lambda: op.create_index(
                "ix_san_phage_panel_result_phage_id",
                "san_phage_panel_result",
                ["phage_id"],
                unique=False,
            ),
        ],
    )

    op.execute("PRAGMA foreign_keys=ON")
