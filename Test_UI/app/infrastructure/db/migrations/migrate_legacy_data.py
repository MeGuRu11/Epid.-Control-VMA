from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from app.infrastructure.db.engine import create_all, init_engine


def migrate_legacy_data(db_path: Path) -> None:
    engine = init_engine(db_path)
    create_all(engine)
    with engine.begin() as conn:
        # Ensure default material type exists.
        conn.execute(
            text(
                """
                INSERT INTO ref_material_types(code, name)
                SELECT 'BLD', 'Кровь'
                WHERE NOT EXISTS (SELECT 1 FROM ref_material_types WHERE code='BLD')
                """
            )
        )
        material_id = conn.execute(
            text("SELECT id FROM ref_material_types WHERE code='BLD' LIMIT 1")
        ).scalar_one()
        conn.execute(
            text(
                """
                UPDATE lab_sample
                SET material_type_id = :material_id
                WHERE material_type_id IS NULL
                """
            ),
            {"material_id": material_id},
        )

        # Normalize nullable text defaults for legacy rows.
        conn.execute(
            text(
                """
                UPDATE emr_case
                SET department = 'н/д'
                WHERE department IS NULL OR TRIM(department) = ''
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE patients
                SET full_name = 'н/д'
                WHERE full_name IS NULL OR TRIM(full_name) = ''
                """
            )
        )
        # Post-checks for integrity.
        integrity = conn.execute(text("PRAGMA integrity_check;")).scalar_one()
        if str(integrity).lower() != "ok":
            raise RuntimeError(f"integrity_check failed: {integrity}")
        fk_rows = conn.execute(text("PRAGMA foreign_key_check;")).fetchall()
        if fk_rows:
            raise RuntimeError(f"foreign_key_check failed: {len(fk_rows)} violations")
    engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate legacy EpiSafe sqlite data to current schema.")
    parser.add_argument("db_path", type=Path, help="Path to sqlite db file")
    args = parser.parse_args()
    migrate_legacy_data(args.db_path)
    print(f"Legacy migration complete: {args.db_path}")
