from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from app.application.services import backup_service as backup_service_module
from app.application.services.backup_service import BackupService
from app.application.services.exchange_service import ExchangeService
from app.application.services.form100_service_v2 import Form100ServiceV2
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from tests.integration.test_exchange_service_import_reports import (
    make_session_factory as make_exchange_session_factory,
    seed_actor,
)
from tests.integration.test_form100_v2_service import (
    make_create_request,
    make_session_factory as make_form100_session_factory,
    seed_users,
)


def _assert_no_absolute_or_windows_paths(value: Any) -> None:
    serialized = json.dumps(value, ensure_ascii=False, default=str)
    assert ":\\" not in serialized
    assert "\\" not in serialized
    assert "C:/" not in serialized

    def _walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key in {"path", "name", "root", "artifact_path", "file_path"} and isinstance(child, str):
                    if key == "root":
                        assert child == "."
                    else:
                        assert not child.startswith("/")
                        assert not Path(child).is_absolute()
                        assert "\\" not in child
                _walk(child)
        elif isinstance(item, list):
            for child in item:
                _walk(child)

    _walk(value)


def test_last_backup_json_uses_relative_posix_path_and_reads_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(backup_service_module, "DATA_DIR", tmp_path)
    db_path = tmp_path / "app.db"
    db_path.write_bytes(b"SQLite format 3\x00" + b"\x00" * 84)
    monkeypatch.setattr(backup_service_module, "DB_FILE", db_path)
    service = BackupService(audit_repo=AuditLogRepository())
    monkeypatch.setattr(service, "_require_admin_access", lambda **_kwargs: None)
    monkeypatch.setattr(service, "_audit_event", lambda *_args, **_kwargs: None)

    backup_path = service.create_backup(actor_id=1, reason="manual")

    payload = json.loads(service._meta_path.read_text(encoding="utf-8"))
    assert payload["path"] == backup_path.name
    _assert_no_absolute_or_windows_paths(payload)
    last_backup = service.get_last_backup()
    assert last_backup is not None
    assert last_backup.path == backup_path


def test_exchange_zip_manifest_contains_only_relative_posix_paths(tmp_path: Path) -> None:
    session_factory = make_exchange_session_factory(tmp_path / "exchange_manifest_paths.db")
    actor_id = seed_actor(session_factory)
    service = ExchangeService(session_factory=session_factory)
    zip_path = tmp_path / "exchange" / "full_export.zip"

    service.export_zip(zip_path, exported_by="exchange_admin", actor_id=actor_id)

    with zipfile.ZipFile(zip_path, "r") as zf:
        manifest = json.loads(zf.read("manifest.json"))

    assert "root" not in manifest or manifest["root"] == "."
    _assert_no_absolute_or_windows_paths(manifest)


def test_form100_zip_manifest_and_payload_contain_only_relative_posix_paths(tmp_path: Path) -> None:
    session_factory = make_form100_session_factory(tmp_path / "form100_manifest_paths.db")
    admin_id, operator_id = seed_users(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)
    created = service.create_card(make_create_request(), actor_id=operator_id)
    zip_path = tmp_path / "form100" / "form100_package.zip"

    service.export_package_zip(file_path=zip_path, actor_id=admin_id, card_id=created.id, exported_by="admin")

    with zipfile.ZipFile(zip_path, "r") as zf:
        manifest = json.loads(zf.read("manifest.json"))
        form100_payload = json.loads(zf.read("form100.json"))

    assert "root" not in manifest or manifest["root"] == "."
    _assert_no_absolute_or_windows_paths(manifest)
    _assert_no_absolute_or_windows_paths(form100_payload)
