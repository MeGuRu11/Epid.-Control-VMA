from __future__ import annotations

from typing import cast

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QWidget

from app.application.exceptions import AppError
from app.application.services.setup_service import SetupService
from app.ui.first_run_dialog import FirstRunDialog


class _SetupServiceStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def create_initial_user(self, *, login: str, password: str) -> None:
        self.calls.append((login, password))


class _FailingSetupService:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def create_initial_user(self, *, login: str, password: str) -> None:
        self.calls.append((login, password))
        raise self.error


def _create_button(dialog: FirstRunDialog) -> QWidget:
    buttons = dialog.findChild(QDialogButtonBox)
    assert buttons is not None
    button = buttons.button(QDialogButtonBox.StandardButton.Ok)
    assert button is not None
    assert isinstance(button, QWidget)
    return button


def test_first_run_dialog_accepts_valid_admin_and_hides(qapp) -> None:
    setup = _SetupServiceStub()
    dialog = FirstRunDialog(setup_service=cast(SetupService, setup))
    try:
        dialog.show()
        qapp.processEvents()

        dialog.login_edit.setText("admin")
        dialog.password_edit.setText("password123")
        dialog.password_confirm.setText("password123")

        QTest.mouseClick(_create_button(dialog), Qt.MouseButton.LeftButton)
        qapp.processEvents()

        assert setup.calls == [("admin", "password123")]
        assert dialog.result() == int(QDialog.DialogCode.Accepted)
        assert not dialog.isVisible()
    finally:
        dialog.close()


@pytest.mark.parametrize(
    ("error", "expected_message"),
    [
        (ValueError("Логин уже занят"), "Логин уже занят"),
        (AppError("service unavailable"), "Не удалось создать администратора"),
    ],
)
def test_first_run_dialog_keeps_window_visible_on_create_error(
    qapp,
    error: Exception,
    expected_message: str,
) -> None:
    setup = _FailingSetupService(error)
    dialog = FirstRunDialog(setup_service=cast(SetupService, setup))
    try:
        dialog.show()
        qapp.processEvents()

        dialog.login_edit.setText("admin")
        dialog.password_edit.setText("password123")
        dialog.password_confirm.setText("password123")

        QTest.mouseClick(_create_button(dialog), Qt.MouseButton.LeftButton)
        qapp.processEvents()

        assert setup.calls == [("admin", "password123")]
        assert dialog.isVisible()
        assert dialog.result() == int(QDialog.DialogCode.Rejected)
        assert dialog.error_label.isVisible()
        assert expected_message in dialog.error_label.text()
    finally:
        dialog.close()
