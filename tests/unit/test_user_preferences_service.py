from __future__ import annotations

from pathlib import Path

from app.application.dto.user_preferences_dto import UserPreferences
from app.application.services.user_preferences_service import UserPreferencesService
from app.config import Settings
from app.infrastructure.preferences.preferences_repository import PreferencesRepository


def _make_service(tmp_path: Path, settings: Settings | None = None) -> UserPreferencesService:
    repo = PreferencesRepository(tmp_path)
    return UserPreferencesService(
        repository=repo,
        defaults_settings=settings or Settings(),
        data_dir=tmp_path,
    )


# ----------------------------------------------------------------------
# Initial load
# ----------------------------------------------------------------------


def test_initial_load_uses_defaults_when_no_file(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    current = service.current

    assert current.ui_density == "normal"
    assert current.session_timeout_minutes == 30
    # Дефолтные пути заполнены, не пустые.
    assert current.pdf_export_dir != ""
    assert current.backup_dir != ""


def test_initial_load_inherits_settings_defaults(tmp_path: Path) -> None:
    settings_with_compact = Settings()
    # Settings — frozen, поэтому через replace.
    from dataclasses import replace

    custom = replace(settings_with_compact, ui_density="compact", session_timeout_minutes=120)

    service = _make_service(tmp_path, settings=custom)

    assert service.current.ui_density == "compact"
    assert service.current.session_timeout_minutes == 120


def test_initial_load_reads_existing_file(tmp_path: Path) -> None:
    repo = PreferencesRepository(tmp_path)
    repo.save({"ui_density": "compact", "session_timeout_minutes": 90})

    service = UserPreferencesService(
        repository=repo,
        defaults_settings=Settings(),
        data_dir=tmp_path,
    )

    assert service.current.ui_density == "compact"
    assert service.current.session_timeout_minutes == 90


def test_initial_load_merges_partial_file_with_defaults(tmp_path: Path) -> None:
    """Если в файле только часть полей — остальные берутся из дефолтов."""
    repo = PreferencesRepository(tmp_path)
    repo.save({"ui_density": "compact"})

    service = UserPreferencesService(
        repository=repo,
        defaults_settings=Settings(),
        data_dir=tmp_path,
    )

    assert service.current.ui_density == "compact"
    # Дефолты подставились.
    assert service.current.session_timeout_minutes == 30
    assert service.current.auto_backup_enabled is True


# ----------------------------------------------------------------------
# Update / persistence
# ----------------------------------------------------------------------


def test_update_persists_to_disk(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    new_prefs = service.current.with_updates(ui_density="compact")

    service.update(new_prefs)

    # Перечитываем «с диска» через свежий сервис.
    fresh = _make_service(tmp_path)
    assert fresh.current.ui_density == "compact"


def test_update_returns_current_value(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    new_prefs = service.current.with_updates(toasts_enabled=False)

    returned = service.update(new_prefs)

    assert returned.toasts_enabled is False
    assert service.current.toasts_enabled is False


def test_reset_to_defaults_removes_file_and_restores_defaults(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    service.update(service.current.with_updates(ui_density="compact"))

    service.reset_to_defaults()

    assert not (tmp_path / "preferences.json").exists()
    assert service.current.ui_density == "normal"


def test_reload_re_reads_disk(tmp_path: Path) -> None:
    service_a = _make_service(tmp_path)
    service_b = _make_service(tmp_path)

    # service_b пишет на диск.
    service_b.update(service_b.current.with_updates(session_timeout_minutes=60))

    # service_a об этом не знает.
    assert service_a.current.session_timeout_minutes == 30

    # После reload — увидит изменения.
    service_a.reload()
    assert service_a.current.session_timeout_minutes == 60


# ----------------------------------------------------------------------
# Window geometry shortcut
# ----------------------------------------------------------------------


def test_update_window_geometry_persists_when_remember_enabled(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    service.update_window_geometry((10, 20, 1024, 768))

    fresh = _make_service(tmp_path)
    assert fresh.current.last_window_geometry == (10, 20, 1024, 768)


def test_update_window_geometry_skipped_when_disabled(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    service.update(service.current.with_updates(remember_window_geometry=False))

    service.update_window_geometry((10, 20, 1024, 768))

    fresh = _make_service(tmp_path)
    assert fresh.current.last_window_geometry is None


def test_update_window_geometry_is_idempotent(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    geom = (5, 5, 800, 600)
    service.update_window_geometry(geom)
    file_path = tmp_path / "preferences.json"
    mtime_before = file_path.stat().st_mtime_ns

    # Та же геометрия — повторная запись не нужна.
    service.update_window_geometry(geom)
    mtime_after = file_path.stat().st_mtime_ns

    assert mtime_after == mtime_before


# ----------------------------------------------------------------------
# Observers
# ----------------------------------------------------------------------


def test_subscribe_invokes_observer_on_update(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    received: list[UserPreferences] = []
    service.subscribe(received.append)

    service.update(service.current.with_updates(ui_density="compact"))

    assert len(received) == 1
    assert received[0].ui_density == "compact"


def test_subscribe_invokes_observer_on_reset(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    received: list[UserPreferences] = []
    service.subscribe(received.append)

    service.reset_to_defaults()

    assert len(received) == 1


def test_subscribe_does_not_notify_for_window_geometry_only(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    received: list[UserPreferences] = []
    service.subscribe(received.append)

    service.update_window_geometry((1, 2, 3, 4))

    assert received == []


def test_unsubscribe_stops_notifications(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    received: list[UserPreferences] = []
    unsubscribe = service.subscribe(received.append)

    unsubscribe()
    service.update(service.current.with_updates(ui_density="compact"))

    assert received == []


def test_unsubscribe_is_idempotent(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    unsubscribe = service.subscribe(lambda _p: None)
    unsubscribe()
    # Второй вызов не должен падать.
    unsubscribe()


def test_observer_exception_does_not_break_other_observers(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    received: list[UserPreferences] = []

    def boom(_p: UserPreferences) -> None:
        raise RuntimeError("observer crashed")

    service.subscribe(boom)
    service.subscribe(received.append)

    # Update проходит, второй observer получает уведомление.
    service.update(service.current.with_updates(ui_density="compact"))

    assert len(received) == 1
