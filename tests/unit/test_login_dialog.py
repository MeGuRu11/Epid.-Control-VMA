from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from app.application.dto.auth_dto import SessionContext
from app.application.services.auth_service import AuthService
from app.ui.login_dialog import LoginDialog


class _FailingAuthService:
    def __init__(self, message: str = "Неверный логин или пароль") -> None:
        self.message = message

    def login(self, _request):
        raise ValueError(self.message)


class _ConditionalAuthService:
    def login(self, request):
        if request.password != "StrongPass1":
            raise ValueError("Неверный логин или пароль")
        return SessionContext(user_id=1, login=request.login, role="admin")


def test_login_dialog_keeps_windowed_geometry_within_available_screen(qapp) -> None:
    dialog = LoginDialog(auth_service=cast(AuthService, SimpleNamespace()))
    screen = dialog.screen() or qapp.primaryScreen()

    assert screen is not None

    geometry = screen.availableGeometry()

    assert dialog.minimumWidth() < geometry.width()
    assert dialog.minimumHeight() < geometry.height()
    assert dialog.width() < geometry.width()
    assert dialog.height() < geometry.height()


def test_login_dialog_shows_redesigned_banner_on_invalid_credentials_when_pressing_enter(qapp) -> None:
    dialog = LoginDialog(auth_service=cast(AuthService, _FailingAuthService()))
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
    assert dialog.error_banner.isVisible()
    assert dialog.error_message.text() == "Неверный логин или пароль"


def test_login_dialog_shows_redesigned_banner_on_invalid_credentials_when_clicking_login(qapp) -> None:
    dialog = LoginDialog(auth_service=cast(AuthService, _FailingAuthService()))
    dialog.show()
    qapp.processEvents()

    dialog.login_edit.setText("admin")
    dialog.password_edit.setText("admin1234")

    QTest.mouseClick(dialog._login_btn, Qt.MouseButton.LeftButton)
    qapp.processEvents()

    assert dialog.isVisible()
    assert dialog.session is None
    assert dialog.error_banner.isVisible()
    assert dialog.error_message.text() == "Неверный логин или пароль"


def test_login_dialog_shows_redesigned_banner_when_fields_are_empty(qapp) -> None:
    dialog = LoginDialog(auth_service=cast(AuthService, _FailingAuthService()))
    dialog.show()
    qapp.processEvents()

    QTest.mouseClick(dialog._login_btn, Qt.MouseButton.LeftButton)
    qapp.processEvents()

    assert dialog.session is None
    assert dialog.error_banner.isVisible()
    assert dialog.error_message.text() == "Введите логин и пароль."


def test_login_dialog_hides_banner_after_successful_login(qapp) -> None:
    dialog = LoginDialog(auth_service=cast(AuthService, _ConditionalAuthService()))
    dialog.show()
    qapp.processEvents()

    dialog.login_edit.setText("admin")
    dialog.password_edit.setText("bad-password")
    QTest.mouseClick(dialog._login_btn, Qt.MouseButton.LeftButton)
    qapp.processEvents()

    assert dialog.error_banner.isVisible()
    assert dialog.error_message.text() == "Неверный логин или пароль"

    dialog.password_edit.setText("StrongPass1")
    QTest.mouseClick(dialog._login_btn, Qt.MouseButton.LeftButton)
    qapp.processEvents()

    assert dialog.result() == dialog.Accepted
    assert dialog.session is not None
    assert dialog.session.user_id == 1
    assert dialog.session.login == "admin"
    assert dialog.session.role == "admin"
    assert not dialog.error_banner.isVisible()
    assert dialog.error_message.text() == ""
