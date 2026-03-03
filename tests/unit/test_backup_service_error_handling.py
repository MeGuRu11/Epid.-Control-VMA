from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.application.services import backup_service as backup_service_module
from app.application.services.backup_service import BackupService
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository


def _build_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BackupService:
    monkeypatch.setattr(backup_service_module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(backup_service_module, "DB_FILE", tmp_path / "app.db")
    return BackupService(audit_repo=AuditLogRepository())


def test_get_last_backup_returns_none_for_corrupt_meta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _build_service(tmp_path, monkeypatch)
    service._meta_path.write_text("{not-json", encoding="utf-8")

    assert service.get_last_backup() is None


def test_create_backup_falls_back_to_file_copy_when_sqlite_backup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _build_service(tmp_path, monkeypatch)
    source_db = backup_service_module.DB_FILE
    source_db.write_bytes(b"sqlite-fallback-test")

    monkeypatch.setattr(service, "_require_admin_access", lambda **_kwargs: None)
    monkeypatch.setattr(service, "_audit_event", lambda *_args, **_kwargs: None)

    def _failing_sqlite_backup(_source: Path, _target: Path) -> None:
        raise sqlite3.DatabaseError("sqlite backup not available")

    monkeypatch.setattr(service, "_create_sqlite_backup", _failing_sqlite_backup)

    backup_path = service.create_backup(actor_id=1, reason="manual")
    assert backup_path.exists()
    assert backup_path.read_bytes() == source_db.read_bytes()


def test_restore_backup_continues_when_engine_dispose_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _build_service(tmp_path, monkeypatch)
    source_db = backup_service_module.DB_FILE
    source_db.write_bytes(b"old-db")
    backup_file = tmp_path / "restore.db"
    backup_file.write_bytes(b"new-db")

    monkeypatch.setattr(service, "_require_admin_access", lambda **_kwargs: None)
    monkeypatch.setattr(service, "_audit_event", lambda *_args, **_kwargs: None)

    import app.infrastructure.db.session as session_module

    monkeypatch.setattr(session_module, "engine", object())

    service.restore_backup(backup_file, actor_id=1)
    assert source_db.read_bytes() == b"new-db"
