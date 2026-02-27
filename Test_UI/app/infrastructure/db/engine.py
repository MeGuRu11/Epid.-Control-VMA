from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .models_sqlalchemy import Base


def init_engine(db_path: Path) -> Engine:
    url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    engine = create_engine(url, future=True, echo=False)
    with engine.connect() as con:
        con.exec_driver_sql("PRAGMA foreign_keys=ON;")
        con.exec_driver_sql("PRAGMA journal_mode=WAL;")
    return engine


def _table_columns(engine: Engine, table: str) -> set[str]:
    with engine.connect() as con:
        rows = con.exec_driver_sql(f"PRAGMA table_info({table});").fetchall()
    return {str(r[1]) for r in rows}


def _add_column_if_missing(engine: Engine, table: str, column: str, ddl: str) -> None:
    existing = _table_columns(engine, table)
    if column in existing:
        return
    with engine.begin() as con:
        con.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl};")


def _ensure_legacy_compat(engine: Engine) -> None:
    # patients
    _add_column_if_missing(engine, "patients", "category", "TEXT")
    _add_column_if_missing(engine, "patients", "military_unit", "TEXT")
    _add_column_if_missing(engine, "patients", "military_district", "TEXT")

    # emr_case
    _add_column_if_missing(engine, "emr_case", "department_id", "INTEGER")

    # emr_case_version
    _add_column_if_missing(engine, "emr_case_version", "outcome_type", "TEXT")
    _add_column_if_missing(engine, "emr_case_version", "vph_sp_score", "INTEGER")
    _add_column_if_missing(engine, "emr_case_version", "vph_p_or_score", "INTEGER")

    # lab_sample
    _add_column_if_missing(engine, "lab_sample", "emr_case_id", "INTEGER")
    _add_column_if_missing(engine, "lab_sample", "barcode", "TEXT")
    _add_column_if_missing(engine, "lab_sample", "material_type_id", "INTEGER")
    _add_column_if_missing(engine, "lab_sample", "material_location", "TEXT")
    _add_column_if_missing(engine, "lab_sample", "medium", "TEXT")
    _add_column_if_missing(engine, "lab_sample", "study_kind", "TEXT")
    _add_column_if_missing(engine, "lab_sample", "ordered_at", "DATETIME")
    _add_column_if_missing(engine, "lab_sample", "taken_at", "DATETIME")
    _add_column_if_missing(engine, "lab_sample", "delivered_at", "DATETIME")
    _add_column_if_missing(engine, "lab_sample", "growth_result_at", "DATETIME")
    _add_column_if_missing(engine, "lab_sample", "colony_desc", "TEXT")
    _add_column_if_missing(engine, "lab_sample", "microscopy", "TEXT")

    # indexes
    with engine.begin() as con:
        con.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_patients_full_name ON patients(full_name);"
        )
        con.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_emr_case_hospital_case_no ON emr_case(hospital_case_no);"
        )
        con.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_emr_case_version_admission_date ON emr_case_version(admission_date);"
        )
        con.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_emr_case_version_outcome_date ON emr_case_version(outcome_date);"
        )
        con.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_lab_sample_patient_taken ON lab_sample(patient_id, taken_at);"
        )
        con.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_audit_log_event_ts ON audit_log(event_ts);"
        )


def create_all(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    _ensure_legacy_compat(engine)
