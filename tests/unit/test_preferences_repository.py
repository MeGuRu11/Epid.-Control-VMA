from __future__ import annotations

import json
from pathlib import Path

from app.infrastructure.preferences.preferences_repository import (
    PREFERENCES_FILE_NAME,
    PREFERENCES_SCHEMA_VERSION,
    PreferencesRepository,
)


def test_load_returns_none_when_file_missing(tmp_path: Path) -> None:
    repo = PreferencesRepository(tmp_path)
    assert repo.load() is None


def test_save_then_load_roundtrip_preserves_values(tmp_path: Path) -> None:
    repo = PreferencesRepository(tmp_path)
    payload = {"ui_density": "compact", "session_timeout_minutes": 45}
    repo.save(payload)
    loaded = repo.load()
    assert loaded == payload


def test_save_writes_schema_version_and_values(tmp_path: Path) -> None:
    repo = PreferencesRepository(tmp_path)
    repo.save({"ui_density": "normal"})
    raw = json.loads((tmp_path / PREFERENCES_FILE_NAME).read_text(encoding="utf-8"))
    assert raw["schema_version"] == PREFERENCES_SCHEMA_VERSION
    assert raw["values"] == {"ui_density": "normal"}


def test_save_creates_data_dir_if_missing(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "data"
    repo = PreferencesRepository(nested)
    repo.save({"ui_density": "compact"})
    assert (nested / PREFERENCES_FILE_NAME).exists()


def test_load_returns_none_on_malformed_json(tmp_path: Path) -> None:
    file = tmp_path / PREFERENCES_FILE_NAME
    file.write_text("{ not valid json", encoding="utf-8")
    repo = PreferencesRepository(tmp_path)
    assert repo.load() is None


def test_load_returns_none_when_top_level_not_dict(tmp_path: Path) -> None:
    file = tmp_path / PREFERENCES_FILE_NAME
    file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    repo = PreferencesRepository(tmp_path)
    assert repo.load() is None


def test_load_returns_none_on_unknown_schema_version(tmp_path: Path) -> None:
    file = tmp_path / PREFERENCES_FILE_NAME
    payload = {"schema_version": 999, "values": {"ui_density": "compact"}}
    file.write_text(json.dumps(payload), encoding="utf-8")
    repo = PreferencesRepository(tmp_path)
    assert repo.load() is None


def test_load_returns_none_when_values_not_dict(tmp_path: Path) -> None:
    file = tmp_path / PREFERENCES_FILE_NAME
    payload = {"schema_version": PREFERENCES_SCHEMA_VERSION, "values": "string-not-dict"}
    file.write_text(json.dumps(payload), encoding="utf-8")
    repo = PreferencesRepository(tmp_path)
    assert repo.load() is None


def test_delete_removes_file(tmp_path: Path) -> None:
    repo = PreferencesRepository(tmp_path)
    repo.save({"a": 1})
    assert (tmp_path / PREFERENCES_FILE_NAME).exists()
    repo.delete()
    assert not (tmp_path / PREFERENCES_FILE_NAME).exists()


def test_delete_when_file_missing_does_not_raise(tmp_path: Path) -> None:
    repo = PreferencesRepository(tmp_path)
    repo.delete()


def test_save_overwrites_existing_file(tmp_path: Path) -> None:
    repo = PreferencesRepository(tmp_path)
    repo.save({"ui_density": "normal"})
    repo.save({"ui_density": "compact"})
    assert repo.load() == {"ui_density": "compact"}


def test_save_does_not_leave_temp_files_on_success(tmp_path: Path) -> None:
    repo = PreferencesRepository(tmp_path)
    repo.save({"ui_density": "compact"})
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".preferences-")]
    assert leftovers == []


def test_file_path_property_reports_target_path(tmp_path: Path) -> None:
    repo = PreferencesRepository(tmp_path)
    assert repo.file_path == tmp_path / PREFERENCES_FILE_NAME
