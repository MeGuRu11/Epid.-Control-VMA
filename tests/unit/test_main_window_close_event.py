from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any, cast

import pytest
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QWidget

from app.application.dto.auth_dto import SessionContext
from app.ui import main_window as main_window_module
from app.ui.main_window import MainWindow
from app.ui.widgets import logout_dialog as logout_dialog_module


@pytest.fixture
def main_window(monkeypatch, qtbot) -> Iterator[MainWindow]:
    def _stub_init_views(self) -> None:  # noqa: ANN001
        class _FakeHomeView(QWidget):
            def refresh_stats(self) -> None:
                return

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
    qtbot.addWidget(window)
    try:
        yield window
    finally:
        window._close_confirmed = True
        window.close()
        window.deleteLater()


def test_close_event_calls_confirm_exit(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """При обычном закрытии вызывается confirm_exit."""
    called = {"v": False}

    def fake_confirm(_parent: QWidget | None = None) -> bool:
        called["v"] = True
        return False

    monkeypatch.setattr(main_window_module, "confirm_exit", fake_confirm)

    event = QCloseEvent()
    main_window.closeEvent(event)

    assert called["v"] is True
    assert not event.isAccepted()


def test_close_event_accepted_when_confirmed(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """При подтверждении закрытие проходит."""
    monkeypatch.setattr(main_window_module, "confirm_exit", lambda _p=None: True)

    event = QCloseEvent()
    main_window.closeEvent(event)

    assert event.isAccepted()


def test_programmatic_close_skips_confirm(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Флаг _close_confirmed обходит диалог."""
    confirm_called = {"v": False}

    def fake_confirm(_parent: QWidget | None = None) -> bool:
        confirm_called["v"] = True
        return True

    monkeypatch.setattr(
        main_window_module,
        "confirm_exit",
        fake_confirm,
    )
    main_window._close_confirmed = True

    event = QCloseEvent()
    main_window.closeEvent(event)

    assert confirm_called["v"] is False


def test_exit_dialog_default_button_is_cancel(qtbot) -> None:
    """По умолчанию активна кнопка «Отмена»."""
    dlg = logout_dialog_module.ExitConfirmDialog()
    qtbot.addWidget(dlg)

    assert dlg.cancel_btn.isDefault()
    assert not dlg.exit_btn.isDefault()
