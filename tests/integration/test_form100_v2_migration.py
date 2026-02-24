from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, cast

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

MIGRATION_MODULE = "app.infrastructure.db.migrations.versions.0019_form100_v2_schema"


def _run_migration(connection, *, fn_name: str) -> None:
    module = cast(Any, importlib.import_module(MIGRATION_MODULE))
    context = MigrationContext.configure(connection)
    operations = Operations(context)
    original_op = module.op
    try:
        module.op = operations
        getattr(module, fn_name)()
    finally:
        module.op = original_op


def _table_names(connection) -> set[str]:
    rows = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
    return {str(row[0]) for row in rows}


def test_form100_v2_migration_creates_tables_and_migrates_legacy_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "form100_v2_migration.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)

    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        connection.execute(text("CREATE TABLE emr_case (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE form100_card (id TEXT PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE form100_mark (card_id TEXT, created_at TEXT)"))
        connection.execute(text("CREATE TABLE form100_stage (card_id TEXT, received_at TEXT)"))
        connection.execute(text("INSERT INTO form100_card (id) VALUES ('legacy-card-1')"))

        _run_migration(connection, fn_name="upgrade")

        tables_after_upgrade = _table_names(connection)
        assert "form100" in tables_after_upgrade
        assert "form100_data" in tables_after_upgrade

        migrated_cards = connection.execute(text("SELECT id, legacy_card_id FROM form100")).fetchall()
        assert len(migrated_cards) == 1
        assert migrated_cards[0][0] == "legacy-card-1"
        assert migrated_cards[0][1] == "legacy-card-1"

        migrated_data_rows = connection.execute(text("SELECT form100_id FROM form100_data")).fetchall()
        assert len(migrated_data_rows) == 1
        assert migrated_data_rows[0][0] == "legacy-card-1"

        _run_migration(connection, fn_name="downgrade")

        tables_after_downgrade = _table_names(connection)
        assert "form100" not in tables_after_downgrade
        assert "form100_data" not in tables_after_downgrade
        assert "form100_card" in tables_after_downgrade
