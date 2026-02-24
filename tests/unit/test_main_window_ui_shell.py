from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtWidgets import QWidget

from app.application.dto.auth_dto import SessionContext
from app.ui.main_window import MainWindow
from app.ui.widgets.transition_stack import TransitionStack


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
        container=container,
    )
    qapp.processEvents()

    assert isinstance(window._stack, TransitionStack)
    assert window._background is not None
    assert window._foreground is not None


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
        container=container,
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
