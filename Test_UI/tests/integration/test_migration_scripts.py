from __future__ import annotations

from importlib import import_module


def test_migration_modules_importable():
    modules = [
        "app.infrastructure.db.migrations.versions.20260217_0001_baseline_from_current",
        "app.infrastructure.db.migrations.versions.20260217_0002_references_and_emr_children",
        "app.infrastructure.db.migrations.versions.20260217_0003_lab_extended_and_sequences",
        "app.infrastructure.db.migrations.versions.20260217_0004_sanitary_and_reporting_exchange",
    ]
    for mod in modules:
        imported = import_module(mod)
        assert hasattr(imported, "upgrade")
        assert hasattr(imported, "downgrade")

