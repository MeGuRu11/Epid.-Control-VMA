from __future__ import annotations

from pathlib import Path

from app.infrastructure.db.migrations.migrate_legacy_data import migrate_legacy_data


def test_legacy_migration_smoke(tmp_path: Path):
    db_path = tmp_path / "legacy.db"
    migrate_legacy_data(db_path)
    assert db_path.exists()

