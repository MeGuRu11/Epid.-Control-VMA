from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from PySide6.QtWidgets import QToolButton, QWidget

from app.application.dto.auth_dto import SessionContext
from app.application.services.user_preferences_service import UserPreferencesService
from app.config import Settings
from app.infrastructure.preferences.preferences_repository import PreferencesRepository
from app.ui.main_window import MainWindow


def _make_service(tmp_path: Path) -> UserPreferencesService:
    return UserPreferencesService(
        repository=PreferencesRepository(tmp_path),
        defaults_settings=Settings(),
        data_dir=tmp_path,
    )


def _make_minimal_main_window(
    monkeypatch, qapp, container: SimpleNamespace
) -> MainWindow:
    """Build a MainWindow with stubbed views and menu — same trick used by other UI tests."""

    def _stub_init_views(self) -> None:  # noqa: ANN001
        # _set_active_view → _refresh_home вызывает refresh_stats у home_view,
        # поэтому подсовываем подкласс QWidget с этим методом.
        class _FakeHomeView(QWidget):
            def refresh_stats(self) -> None:
                pass

        self._home_view = _FakeHomeView()
        self._emr_form = QWidget()
        self._form100_view = QWidget()
        self._emk_view = QWidget()
        self._lab_view = QWidget()
        self._sanitary_view = QWidget()
        self._analytics_view = QWidget()
        self._exchange_view = QWidget()
        self._ref_view = QWidget()
        self._admin_view = QWidget()
        for view in (
            self._home_view,
            self._emr_form,
            self._form100_view,
            self._emk_view,
            self._lab_view,
            self._sanitary_view,
            self._analytics_view,
            self._exchange_view,
            self._ref_view,
            self._admin_view,
        ):
            self._stack.addWidget(view)
        self._stack.setCurrentWidget(self._home_view)

    monkeypatch.setattr(MainWindow, "_init_views", _stub_init_views)

    window = MainWindow(
        session=SessionContext(user_id=1, login="admin", role="admin"),
        container=cast(Any, container),
    )
    qapp.processEvents()
    window._close_confirmed = True
    return window


def test_main_window_subscribes_to_preferences_service_and_picks_up_timeout(
    monkeypatch, qapp, tmp_path: Path
) -> None:
    service = _make_service(tmp_path)
    service.update(service.current.with_updates(session_timeout_minutes=15))

    container = SimpleNamespace(
        emz_service=SimpleNamespace(),
        patient_service=SimpleNamespace(),
        user_preferences_service=service,
    )
    window = _make_minimal_main_window(monkeypatch, qapp, container)

    assert window._session_timeout_seconds == 15 * 60

    # Изменение настроек на лету должно прийти в окно через subscribe.
    service.update(service.current.with_updates(session_timeout_minutes=90))
    qapp.processEvents()
    assert window._session_timeout_seconds == 90 * 60

    window.close()
    window.deleteLater()
    qapp.processEvents()


def test_main_window_disables_idle_timeout_when_auto_logout_off(
    monkeypatch, qapp, tmp_path: Path
) -> None:
    service = _make_service(tmp_path)
    service.update(service.current.with_updates(auto_logout_enabled=False))

    container = SimpleNamespace(
        emz_service=SimpleNamespace(),
        patient_service=SimpleNamespace(),
        user_preferences_service=service,
    )
    window = _make_minimal_main_window(monkeypatch, qapp, container)

    # Очень большое значение, фактически — никогда.
    assert window._session_timeout_seconds > 10**9

    window.close()
    window.deleteLater()
    qapp.processEvents()


def test_main_window_renders_settings_button_in_navmenu(
    monkeypatch, qapp, tmp_path: Path
) -> None:
    service = _make_service(tmp_path)
    container = SimpleNamespace(
        emz_service=SimpleNamespace(),
        patient_service=SimpleNamespace(),
        user_preferences_service=service,
    )
    window = _make_minimal_main_window(monkeypatch, qapp, container)

    settings_btn = window.findChild(QToolButton, "settingsMenuButton")
    assert settings_btn is not None, "Кнопка настроек должна быть QToolButton в menubar"
    assert settings_btn.toolTip() == "Настройки приложения"
    assert not settings_btn.icon().isNull()

    window.close()
    window.deleteLater()
    qapp.processEvents()


def test_main_window_persists_geometry_on_close_when_remember_enabled(
    monkeypatch, qapp, tmp_path: Path
) -> None:
    service = _make_service(tmp_path)
    container = SimpleNamespace(
        emz_service=SimpleNamespace(),
        patient_service=SimpleNamespace(),
        user_preferences_service=service,
    )
    window = _make_minimal_main_window(monkeypatch, qapp, container)
    window.setGeometry(100, 200, 1024, 768)
    qapp.processEvents()

    window.close()
    qapp.processEvents()
    window.deleteLater()
    qapp.processEvents()

    # Файл настроек должен содержать сохранённую геометрию.
    fresh = _make_service(tmp_path)
    saved = fresh.current.last_window_geometry
    assert saved is not None
    # Проверяем разумные значения, без жёсткой привязки к точным координатам
    # (платформа может скорректировать положение окна).
    assert saved[2] == 1024
    assert saved[3] == 768


def test_main_window_works_when_preferences_service_missing(monkeypatch, qapp) -> None:
    """Совместимость со старыми тестами/моками: окно строится без сервиса настроек."""

    def _stub_init_views(self) -> None:  # noqa: ANN001
        return

    def _stub_build_menu(self) -> None:  # noqa: ANN001
        return

    monkeypatch.setattr(MainWindow, "_init_views", _stub_init_views)
    monkeypatch.setattr(MainWindow, "_build_menu", _stub_build_menu)

    container = SimpleNamespace(
        emz_service=SimpleNamespace(),
        patient_service=SimpleNamespace(),
    )
    window = MainWindow(
        session=SessionContext(user_id=1, login="admin", role="admin"),
        container=cast(Any, container),
    )
    qapp.processEvents()
    window._close_confirmed = True

    # Окно не должно падать при попытке открыть настройки без сервиса.
    window._open_settings()
    qapp.processEvents()

    window.close()
    window.deleteLater()
    qapp.processEvents()
