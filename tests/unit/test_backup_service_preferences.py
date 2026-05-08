"""Тесты интеграции BackupService с UserPreferences.

Проверяем:
- auto_backup_enabled=False → ensure_daily_backup скипает
- frequency="manual" → скипает
- frequency="startup_only" → создаёт только раз
- frequency="startup_daily" → стандартная логика раз в сутки
- backup_retention_count → лишние файлы удаляются
- backup_dir → используется при создании сервиса
- provider exception → сервис работает с дефолтами
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.application.dto.user_preferences_dto import UserPreferences
from app.application.services import backup_service as backup_service_module
from app.application.services.backup_service import BackupService
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _build_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    prefs: UserPreferences | None = None,
    provider_raises: bool = False,
) -> BackupService:
    monkeypatch.setattr(backup_service_module, "DATA_DIR", tmp_path)
    db = tmp_path / "app.db"
    db.write_bytes(b"SQLite format 3\x00" + b"\x00" * 84)
    monkeypatch.setattr(backup_service_module, "DB_FILE", db)

    def _provider() -> UserPreferences:
        if provider_raises:
            raise RuntimeError("provider crash")
        return prefs or UserPreferences()

    return BackupService(
        audit_repo=AuditLogRepository(),
        preferences_provider=_provider if (prefs is not None or provider_raises) else None,
    )


def _admin_actor(service: BackupService, monkeypatch: pytest.MonkeyPatch) -> int:
    """Мокнуть admin-резолвер и аудит, чтобы create_backup не требовал реальной БД."""
    monkeypatch.setattr(service, "_resolve_system_actor_id", lambda: 1)
    monkeypatch.setattr(service, "_require_admin_access", lambda **_: None)
    monkeypatch.setattr(service, "_audit_event", lambda *_a, **_kw: None)
    return 1


# ------------------------------------------------------------------
# ensure_daily_backup — auto_backup_enabled
# ------------------------------------------------------------------


def test_disabled_auto_backup_skips_ensure_daily_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefs = UserPreferences(auto_backup_enabled=False)
    service = _build_service(tmp_path, monkeypatch, prefs=prefs)
    _admin_actor(service, monkeypatch)

    result = service.ensure_daily_backup()

    assert result is False
    assert list(service.backup_dir.glob("app_*.db")) == []


# ------------------------------------------------------------------
# ensure_daily_backup — frequency modes
# ------------------------------------------------------------------


def test_manual_frequency_never_creates_auto_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefs = UserPreferences(auto_backup_enabled=True, auto_backup_frequency="manual")
    service = _build_service(tmp_path, monkeypatch, prefs=prefs)
    _admin_actor(service, monkeypatch)

    result = service.ensure_daily_backup()

    assert result is False
    assert list(service.backup_dir.glob("app_*.db")) == []


def test_startup_only_creates_backup_when_none_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefs = UserPreferences(auto_backup_enabled=True, auto_backup_frequency="startup_only")
    service = _build_service(tmp_path, monkeypatch, prefs=prefs)
    _admin_actor(service, monkeypatch)

    result = service.ensure_daily_backup()

    assert result is True
    assert len(list(service.backup_dir.glob("app_*.db"))) == 1


def test_startup_only_does_not_create_backup_when_one_already_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefs = UserPreferences(auto_backup_enabled=True, auto_backup_frequency="startup_only")
    service = _build_service(tmp_path, monkeypatch, prefs=prefs)
    _admin_actor(service, monkeypatch)

    # Первый запуск — создаёт.
    service.ensure_daily_backup()
    count_after_first = len(list(service.backup_dir.glob("app_*.db")))

    # Второй запуск — пропускает (есть last backup).
    result = service.ensure_daily_backup()

    assert result is False
    assert len(list(service.backup_dir.glob("app_*.db"))) == count_after_first


def test_startup_daily_skips_when_backup_is_fresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefs = UserPreferences(auto_backup_enabled=True, auto_backup_frequency="startup_daily")
    service = _build_service(tmp_path, monkeypatch, prefs=prefs)
    _admin_actor(service, monkeypatch)

    # Создаём первый бэкап.
    service.ensure_daily_backup()

    # Второй вызов в тот же «день» — пропускает.
    result = service.ensure_daily_backup()

    assert result is False


# ------------------------------------------------------------------
# Retention (backup_retention_count)
# ------------------------------------------------------------------


def _seed_old_backups(service: BackupService, count: int) -> list[Path]:
    """Создать count старых файлов без вызова create_backup (без require_admin)."""
    paths = []
    for i in range(count):
        # Разные временные метки (sec resolution)
        ts = f"20250101_10000{i}"
        p = service.backup_dir / f"app_{ts}.db"
        p.write_bytes(b"\x00" * 64)
        paths.append(p)
        time.sleep(0.01)  # небольшой интервал для sort stability
    return paths


def test_create_backup_enforces_retention_keeps_newest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefs = UserPreferences(
        auto_backup_enabled=True,
        backup_retention_count=3,
    )
    service = _build_service(tmp_path, monkeypatch, prefs=prefs)
    _admin_actor(service, monkeypatch)

    # Сидируем 4 старых файла.
    _seed_old_backups(service, 4)

    # Создаём ещё один (итого 5) — retention должен оставить только 3.
    service.create_backup(actor_id=1, reason="manual")
    remaining = list(service.backup_dir.glob("app_*.db"))

    assert len(remaining) == 3


def test_create_backup_retention_one_keeps_only_the_newest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefs = UserPreferences(backup_retention_count=1)
    service = _build_service(tmp_path, monkeypatch, prefs=prefs)
    _admin_actor(service, monkeypatch)

    _seed_old_backups(service, 3)
    service.create_backup(actor_id=1, reason="manual")

    remaining = list(service.backup_dir.glob("app_*.db"))
    assert len(remaining) == 1


def test_create_backup_without_provider_keeps_all_backups(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Без провайдера — retention не применяется (обратная совместимость)."""
    service = _build_service(tmp_path, monkeypatch)  # no prefs
    _admin_actor(service, monkeypatch)

    _seed_old_backups(service, 5)
    service.create_backup(actor_id=1, reason="manual")

    # Retention не применялся → 5 + 1 = 6 файлов.
    remaining = list(service.backup_dir.glob("app_*.db"))
    assert len(remaining) == 6


# ------------------------------------------------------------------
# backup_dir из настроек
# ------------------------------------------------------------------


def test_backup_dir_uses_configured_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom = tmp_path / "my_backups"
    prefs = UserPreferences(backup_dir=str(custom))
    service = _build_service(tmp_path, monkeypatch, prefs=prefs)

    assert service.backup_dir == custom
    assert custom.is_dir()


def test_backup_dir_falls_back_when_configured_path_is_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Путь с невалидными символами (на Linux) — или просто несуществующий внутри root.
    prefs = UserPreferences(backup_dir="/proc/sys/kernel/invalid_backup_path_xyz")
    service = _build_service(tmp_path, monkeypatch, prefs=prefs)

    # Откат к DATA_DIR/backups.
    assert service.backup_dir == tmp_path / "backups"


def test_backup_dir_empty_string_uses_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefs = UserPreferences(backup_dir="")
    service = _build_service(tmp_path, monkeypatch, prefs=prefs)

    assert service.backup_dir == tmp_path / "backups"


# ------------------------------------------------------------------
# Безопасность: исключение в провайдере не ломает сервис
# ------------------------------------------------------------------


def test_provider_exception_does_not_crash_ensure_daily_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _build_service(tmp_path, monkeypatch, provider_raises=True)
    _admin_actor(service, monkeypatch)

    # Не должно поднять исключение — работает как без провайдера.
    result = service.ensure_daily_backup()
    assert isinstance(result, bool)


def test_provider_exception_does_not_crash_create_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _build_service(tmp_path, monkeypatch, provider_raises=True)
    _admin_actor(service, monkeypatch)

    # create_backup не должен падать даже если провайдер сломан.
    path = service.create_backup(actor_id=1, reason="manual")
    assert path.exists()
