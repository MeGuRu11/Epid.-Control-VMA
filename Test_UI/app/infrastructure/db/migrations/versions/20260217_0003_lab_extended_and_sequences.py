"""lab_extended_and_sequences

Revision ID: 20260217_0003
Revises: 20260217_0002
Create Date: 2026-02-17
"""

from __future__ import annotations

from alembic import op

revision = "20260217_0003"
down_revision = "20260217_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_lab_number_sequence_date_material ON lab_number_sequence(seq_date, material_type_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_lab_sample_patient_taken ON lab_sample(patient_id, taken_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lab_sample_material_taken ON lab_sample(material_type_id, taken_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lab_sample_growth_result ON lab_sample(growth_flag, growth_result_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lab_sample_emr_case ON lab_sample(emr_case_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_lab_microbe_isolation_mo ON lab_microbe_isolation(microorganism_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_lab_abx_susceptibility_abx_ris ON lab_abx_susceptibility(antibiotic_id, ris)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_lab_abx_susceptibility_group_ris ON lab_abx_susceptibility(group_id, ris)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lab_phage_panel_phage ON lab_phage_panel_result(phage_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_lab_number_sequence_date_material")
    op.execute("DROP INDEX IF EXISTS ix_lab_sample_patient_taken")
    op.execute("DROP INDEX IF EXISTS ix_lab_sample_material_taken")
    op.execute("DROP INDEX IF EXISTS ix_lab_sample_growth_result")
    op.execute("DROP INDEX IF EXISTS ix_lab_sample_emr_case")
    op.execute("DROP INDEX IF EXISTS ix_lab_microbe_isolation_mo")
    op.execute("DROP INDEX IF EXISTS ix_lab_abx_susceptibility_abx_ris")
    op.execute("DROP INDEX IF EXISTS ix_lab_abx_susceptibility_group_ris")
    op.execute("DROP INDEX IF EXISTS ix_lab_phage_panel_phage")

