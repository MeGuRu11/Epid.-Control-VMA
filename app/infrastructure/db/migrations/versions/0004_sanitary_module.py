"""Sanitary microbiology tables"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_sanitary_module"
down_revision = "0003_lab_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sanitary_sample",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("room", sa.String()),
        sa.Column("sampling_point", sa.String(), nullable=False),
        sa.Column("lab_no", sa.String(), nullable=False, unique=True),
        sa.Column("barcode", sa.String()),
        sa.Column("medium", sa.String()),
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
        "san_microbe_isolation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sanitary_sample_id", sa.Integer(), sa.ForeignKey("sanitary_sample.id"), nullable=False),
        sa.Column("microorganism_id", sa.Integer(), sa.ForeignKey("ref_microorganisms.id")),
        sa.Column("microorganism_free", sa.Text()),
        sa.Column("notes", sa.Text()),
    )

    op.create_table(
        "san_abx_susceptibility",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sanitary_sample_id", sa.Integer(), sa.ForeignKey("sanitary_sample.id"), nullable=False),
        sa.Column("antibiotic_id", sa.Integer(), sa.ForeignKey("ref_antibiotics.id"), nullable=False),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("ref_antibiotic_groups.id")),
        sa.Column("ris", sa.String(), sa.CheckConstraint("ris in ('R','I','S')")),
        sa.Column("mic_mg_l", sa.Integer()),
        sa.Column("method", sa.String()),
    )

    op.create_table(
        "san_phage_panel_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sanitary_sample_id", sa.Integer(), sa.ForeignKey("sanitary_sample.id"), nullable=False),
        sa.Column("phage_id", sa.Integer(), sa.ForeignKey("ref_phages.id")),
        sa.Column("phage_free", sa.Text()),
        sa.Column("lysis_diameter_mm", sa.Integer()),
    )

    op.create_index("ix_sanitary_sample_department_id_taken_at", "sanitary_sample", ["department_id", "taken_at"], unique=False)
    op.create_index("ix_sanitary_sample_growth_flag_growth_result_at", "sanitary_sample", ["growth_flag", "growth_result_at"], unique=False)

    op.create_index("ix_san_microbe_isolation_sanitary_sample_id", "san_microbe_isolation", ["sanitary_sample_id"], unique=False)
    op.create_index("ix_san_microbe_isolation_microorganism_id", "san_microbe_isolation", ["microorganism_id"], unique=False)

    op.create_index("ix_san_abx_susceptibility_sanitary_sample_id", "san_abx_susceptibility", ["sanitary_sample_id"], unique=False)
    op.create_index("ix_san_abx_susceptibility_antibiotic_id_ris", "san_abx_susceptibility", ["antibiotic_id", "ris"], unique=False)
    op.create_index("ix_san_abx_susceptibility_group_id_ris", "san_abx_susceptibility", ["group_id", "ris"], unique=False)

    op.create_index("ix_san_phage_panel_result_sanitary_sample_id", "san_phage_panel_result", ["sanitary_sample_id"], unique=False)
    op.create_index("ix_san_phage_panel_result_phage_id", "san_phage_panel_result", ["phage_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_san_phage_panel_result_phage_id", table_name="san_phage_panel_result")
    op.drop_index("ix_san_phage_panel_result_sanitary_sample_id", table_name="san_phage_panel_result")
    op.drop_table("san_phage_panel_result")

    op.drop_index("ix_san_abx_susceptibility_group_id_ris", table_name="san_abx_susceptibility")
    op.drop_index("ix_san_abx_susceptibility_antibiotic_id_ris", table_name="san_abx_susceptibility")
    op.drop_index("ix_san_abx_susceptibility_sanitary_sample_id", table_name="san_abx_susceptibility")
    op.drop_table("san_abx_susceptibility")

    op.drop_index("ix_san_microbe_isolation_microorganism_id", table_name="san_microbe_isolation")
    op.drop_index("ix_san_microbe_isolation_sanitary_sample_id", table_name="san_microbe_isolation")
    op.drop_table("san_microbe_isolation")

    op.drop_index("ix_sanitary_sample_growth_flag_growth_result_at", table_name="sanitary_sample")
    op.drop_index("ix_sanitary_sample_department_id_taken_at", table_name="sanitary_sample")
    op.drop_table("sanitary_sample")
