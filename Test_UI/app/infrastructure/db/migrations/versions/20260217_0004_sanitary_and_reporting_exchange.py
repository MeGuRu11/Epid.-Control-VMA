"""sanitary_and_reporting_exchange

Revision ID: 20260217_0004
Revises: 20260217_0003
Create Date: 2026-02-17
"""

from __future__ import annotations

from alembic import op

revision = "20260217_0004"
down_revision = "20260217_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_sanitary_sample_dep_taken ON sanitary_sample(department_id, taken_at)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sanitary_sample_growth_result ON sanitary_sample(growth_flag, growth_result_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_san_microbe_isolation_mo ON san_microbe_isolation(microorganism_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_san_abx_susceptibility_abx_ris ON san_abx_susceptibility(antibiotic_id, ris)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_san_abx_susceptibility_group_ris ON san_abx_susceptibility(group_id, ris)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_san_phage_panel_phage ON san_phage_panel_result(phage_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_report_run_created_at ON report_run(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_report_run_type_created_at ON report_run(report_type, created_at)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_data_exchange_direction_created_at ON data_exchange_package(direction, created_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_event_ts ON audit_log(event_ts)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_user_event_ts ON audit_log(user_id, event_ts)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_entity ON audit_log(entity_type, entity_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_sanitary_sample_dep_taken")
    op.execute("DROP INDEX IF EXISTS ix_sanitary_sample_growth_result")
    op.execute("DROP INDEX IF EXISTS ix_san_microbe_isolation_mo")
    op.execute("DROP INDEX IF EXISTS ix_san_abx_susceptibility_abx_ris")
    op.execute("DROP INDEX IF EXISTS ix_san_abx_susceptibility_group_ris")
    op.execute("DROP INDEX IF EXISTS ix_san_phage_panel_phage")
    op.execute("DROP INDEX IF EXISTS ix_report_run_created_at")
    op.execute("DROP INDEX IF EXISTS ix_report_run_type_created_at")
    op.execute("DROP INDEX IF EXISTS ix_data_exchange_direction_created_at")
    op.execute("DROP INDEX IF EXISTS ix_audit_log_event_ts")
    op.execute("DROP INDEX IF EXISTS ix_audit_log_user_event_ts")
    op.execute("DROP INDEX IF EXISTS ix_audit_log_entity")

