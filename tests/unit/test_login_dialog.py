from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from app.application.services.auth_service import AuthService
from app.ui.login_dialog import LoginDialog


def test_login_dialog_keeps_windowed_geometry_within_available_screen(qapp) -> None:
    dialog = LoginDialog(auth_service=cast(AuthService, SimpleNamespace()))
    screen = dialog.screen() or qapp.primaryScreen()

    assert screen is not None

    geometry = screen.availableGeometry()

    assert dialog.minimumWidth() < geometry.width()
    assert dialog.minimumHeight() < geometry.height()
    assert dialog.width() < geometry.width()
    assert dialog.height() < geometry.height()


def test_login_dialog_keeps_open_on_invalid_credentials_when_pressing_enter(qapp) -> None:
    class _AuthServiceStub:
        def login(self, _request):
            raise ValueError("Неверный логин или пароль")

    dialog = LoginDialog(auth_service=cast(AuthService, _AuthServiceStub()))
    dialog.show()
    qapp.processEvents()

    dialog.login_edit.setText("admin")
    dialog.password_edit.setText("admin1234")
    dialog.password_edit.setFocus()
    qapp.processEvents()

    QTest.keyClick(dialog.password_edit, Qt.Key.Key_Return)
    qapp.processEvents()

    assert dialog.isVisible()
    assert dialog.session is None
    assert dialog.error_label.isVisible()
    assert dialog.error_label.text() == "Неверный логин или пароль"
