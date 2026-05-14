from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QPushButton, QWidget

from app.application.dto.auth_dto import SessionContext
from app.config import Settings
from app.ui.main_window import MainWindow, NavMenuBar
from app.ui.theme import apply_theme
from app.ui.widgets.transition_stack import TransitionStack


def _close_widget(qapp, widget: QWidget) -> None:
    if hasattr(widget, "_close_confirmed"):
        widget._close_confirmed = True
    widget.close()
    widget.deleteLater()
    qapp.processEvents()


def test_main_window_uses_transition_stack_and_shell_layers(monkeypatch, qapp) -> None:
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

    assert isinstance(window._stack, TransitionStack)
    assert window._background is not None
    assert window._foreground is not None

    window._context_bar.set_size_change_callback(None)
    _close_widget(qapp, window)


def test_main_window_nav_menu_adapts_titles_on_small_width(monkeypatch, qapp) -> None:
    def _stub_init_views(self) -> None:  # noqa: ANN001
        self._home_view = QWidget()
        self._emr_form = QWidget()
        self._form100_view = QWidget()
        self._emk_view = QWidget()
        self._lab_view = QWidget()
        self._sanitary_view = QWidget()
        self._analytics_view = QWidget()
        self._exchange_view = QWidget()
        self._ref_view = QWidget()
        self._admin_view = QWidget()
        for widget in [
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
        ]:
            self._stack.addWidget(widget)
        self._stack.setCurrentWidget(self._home_view)

    def _stub_set_active_view(self, widget) -> None:  # noqa: ANN001
        self._stack.setCurrentWidget(widget)

    monkeypatch.setattr(MainWindow, "_init_views", _stub_init_views)
    monkeypatch.setattr(MainWindow, "_set_active_view", _stub_set_active_view)

    container = SimpleNamespace(
        emz_service=SimpleNamespace(),
        patient_service=SimpleNamespace(),
    )
    window = MainWindow(
        session=SessionContext(user_id=1, login="admin", role="admin"),
        container=cast(Any, container),
    )
    window.show()
    qapp.processEvents()

    window.resize(960, 700)
    qapp.processEvents()
    window._update_nav_presentation()
    qapp.processEvents()
    assert window._nav_label_mode in {"compact", "mini"}
    assert window.menuBar().property("compactNav") is True
    assert any(action.text() != title for action, title in window._nav_action_titles.items())

    window.resize(2200, 900)
    qapp.processEvents()
    window._update_nav_presentation()
    qapp.processEvents()
    assert window._nav_label_mode == "full"
    assert window.menuBar().property("compactNav") is False
    assert all(action.text() == title for action, title in window._nav_action_titles.items())

    window._context_bar.set_size_change_callback(None)
    _close_widget(qapp, window)


def test_nav_menu_positions_logout_button_evenly(qapp) -> None:
    apply_theme(qapp, Settings())
    menubar = NavMenuBar()
    nav_action = menubar.addAction("Главная")
    button = QPushButton("Выйти")

    menubar.resize(320, 44)
    menubar.set_logout_button(button)
    menubar.show()
    qapp.processEvents()

    top_left = button.mapTo(menubar, QPoint(0, 0))
    nav_rect = menubar.actionGeometry(nav_action)
    logout_center_y = top_left.y() + button.height() // 2

    assert button.height() == 28
    assert top_left.y() >= 0
    assert top_left.y() + button.height() <= menubar.height()
    assert top_left.x() + button.width() <= menubar.width()
    assert abs(logout_center_y - nav_rect.center().y()) <= 2
    assert menubar.cornerWidget(Qt.Corner.TopRightCorner) is not None
    assert menubar.trailing_reserved_width() == button.width() + 16

    _close_widget(qapp, button)
    _close_widget(qapp, menubar)


def test_main_window_idle_timeout_requests_relogin(monkeypatch, qapp) -> None:
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
    window.show()
    qapp.processEvents()

    called: dict[str, bool] = {"value": False}

    def _stub_relogin(*, show_timeout_message: bool) -> None:
        called["value"] = show_timeout_message

    monkeypatch.setattr(window, "_relogin_or_close", _stub_relogin)
    window._session_timeout_seconds = 60
    window._last_activity_at = datetime.now(UTC) - timedelta(seconds=120)

    window._check_idle_timeout()

    assert called["value"] is True
    assert window._idle_timeout_in_progress is False

    window._context_bar.set_size_change_callback(None)
    _close_widget(qapp, window)
