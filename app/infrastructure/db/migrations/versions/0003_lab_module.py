"""Lab module tables"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_lab_module"
down_revision = "0002_references_emr_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lab_number_sequence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seq_date", sa.Date(), nullable=False),
        sa.Column("material_type_id", sa.Integer(), sa.ForeignKey("ref_material_types.id"), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False),
        sa.UniqueConstraint("seq_date", "material_type_id", name="uq_lab_number_sequence"),
    )

    op.create_table(
        "lab_sample",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("emr_case_id", sa.Integer(), sa.ForeignKey("emr_case.id")),
        sa.Column("lab_no", sa.String(), nullable=False, unique=True),
        sa.Column("barcode", sa.String()),
        sa.Column("material_type_id", sa.Integer(), sa.ForeignKey("ref_material_types.id"), nullable=False),
        sa.Column("material_location", sa.String()),
        sa.Column("medium", sa.String()),
        sa.Column("study_kind", sa.String(), sa.CheckConstraint("study_kind in ('primary','repeat')")),
        sa.Column("ordered_at", sa.DateTime()),
        sa.Column("taken_at", sa.DateTime()),
        sa.Column("delivered_at", sa.DateTime()),
        sa.Column("growth_result_at", sa.DateTime()),
        sa.Column("growth_flag", sa.Integer(), sa.CheckConstraint("growth_flag in (0,1)")),
        sa.Column("colony_desc", sa.Text()),
        sa.Column("microscopy", sa.Text()),
        sa.Column("cfu", sa.String()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
    )

    op.create_table(
        "lab_microbe_isolation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lab_sample_id", sa.Integer(), sa.ForeignKey("lab_sample.id"), nullable=False),
        sa.Column("microorganism_id", sa.Integer(), sa.ForeignKey("ref_microorganisms.id")),
        sa.Column("microorganism_free", sa.Text()),
        sa.Column("notes", sa.Text()),
    )

    op.create_table(
        "lab_abx_susceptibility",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lab_sample_id", sa.Integer(), sa.ForeignKey("lab_sample.id"), nullable=False),
        sa.Column("antibiotic_id", sa.Integer(), sa.ForeignKey("ref_antibiotics.id"), nullable=False),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("ref_antibiotic_groups.id")),
        sa.Column("ris", sa.String(), sa.CheckConstraint("ris in ('R','I','S')")),
        sa.Column("mic_mg_l", sa.Integer()),
        sa.Column("method", sa.String()),
    )

    op.create_table(
        "lab_phage_panel_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lab_sample_id", sa.Integer(), sa.ForeignKey("lab_sample.id"), nullable=False),
        sa.Column("phage_id", sa.Integer(), sa.ForeignKey("ref_phages.id")),
        sa.Column("phage_free", sa.Text()),
        sa.Column("lysis_diameter_mm", sa.Integer()),
    )

    op.create_index("ix_lab_sample_patient_id_taken_at", "lab_sample", ["patient_id", "taken_at"], unique=False)
    op.create_index("ix_lab_sample_material_type_id_taken_at", "lab_sample", ["material_type_id", "taken_at"], unique=False)
    op.create_index("ix_lab_sample_growth_flag_growth_result_at", "lab_sample", ["growth_flag", "growth_result_at"], unique=False)
    op.create_index("ix_lab_sample_emr_case_id", "lab_sample", ["emr_case_id"], unique=False)

    op.create_index("ix_lab_microbe_isolation_lab_sample_id", "lab_microbe_isolation", ["lab_sample_id"], unique=False)
    op.create_index("ix_lab_microbe_isolation_microorganism_id", "lab_microbe_isolation", ["microorganism_id"], unique=False)

    op.create_index("ix_lab_abx_susceptibility_lab_sample_id", "lab_abx_susceptibility", ["lab_sample_id"], unique=False)
    op.create_index("ix_lab_abx_susceptibility_antibiotic_id_ris", "lab_abx_susceptibility", ["antibiotic_id", "ris"], unique=False)
    op.create_index("ix_lab_abx_susceptibility_group_id_ris", "lab_abx_susceptibility", ["group_id", "ris"], unique=False)

    op.create_index("ix_lab_phage_panel_result_lab_sample_id", "lab_phage_panel_result", ["lab_sample_id"], unique=False)
    op.create_index("ix_lab_phage_panel_result_phage_id", "lab_phage_panel_result", ["phage_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lab_phage_panel_result_phage_id", table_name="lab_phage_panel_result")
    op.drop_index("ix_lab_phage_panel_result_lab_sample_id", table_name="lab_phage_panel_result")
    op.drop_table("lab_phage_panel_result")

    op.drop_index("ix_lab_abx_susceptibility_group_id_ris", table_name="lab_abx_susceptibility")
    op.drop_index("ix_lab_abx_susceptibility_antibiotic_id_ris", table_name="lab_abx_susceptibility")
    op.drop_index("ix_lab_abx_susceptibility_lab_sample_id", table_name="lab_abx_susceptibility")
    op.drop_table("lab_abx_susceptibility")

    op.drop_index("ix_lab_microbe_isolation_microorganism_id", table_name="lab_microbe_isolation")
    op.drop_index("ix_lab_microbe_isolation_lab_sample_id", table_name="lab_microbe_isolation")
    op.drop_table("lab_microbe_isolation")

    op.drop_index("ix_lab_sample_emr_case_id", table_name="lab_sample")
    op.drop_index("ix_lab_sample_growth_flag_growth_result_at", table_name="lab_sample")
    op.drop_index("ix_lab_sample_material_type_id_taken_at", table_name="lab_sample")
    op.drop_index("ix_lab_sample_patient_id_taken_at", table_name="lab_sample")
    op.drop_table("lab_sample")

    op.drop_table("lab_number_sequence")
