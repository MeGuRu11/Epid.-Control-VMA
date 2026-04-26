from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton

from app.ui.widgets.logout_dialog import LogoutConfirmDialog


def test_logout_confirm_dialog_uses_project_styled_controls(qapp) -> None:
    dialog = LogoutConfirmDialog()

    title = dialog.findChild(QLabel, "logoutDialogTitle")
    body = dialog.findChild(QLabel, "logoutDialogBody")
    icon = dialog.findChild(QLabel, "logoutDialogIcon")
    confirm = dialog.findChild(QPushButton, "logoutConfirmButton")
    cancel = dialog.findChild(QPushButton, "logoutCancelButton")

    assert dialog.objectName() == "logoutConfirmDialog"
    assert title is not None
    assert title.text() == "Завершить сеанс?"
    assert body is not None
    assert "экран входа" in body.text()
    assert icon is not None
    assert icon.text() == "?"
    assert confirm is not None
    assert confirm.text() == "Выйти"
    assert cancel is not None
    assert cancel.text() == "Остаться"
    assert cancel.isDefault() is True

    dialog.close()
