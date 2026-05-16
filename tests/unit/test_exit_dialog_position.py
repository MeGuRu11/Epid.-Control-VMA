from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QDialog, QWidget


def _parent_widget(qtbot: Any, qapp: Any) -> QWidget:
    parent = QWidget()
    parent.setGeometry(100, 120, 900, 640)
    qtbot.addWidget(parent)
    parent.show()
    qapp.processEvents()
    return parent


def test_exit_dialog_centers_on_parent(qtbot: Any, qapp: Any, monkeypatch: Any) -> None:
    from app.ui.widgets import logout_dialog

    parent = _parent_widget(qtbot, qapp)
    captured: list[QDialog] = []

    def fake_exec(self: QDialog) -> QDialog.DialogCode:
        captured.append(self)
        self.close()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(logout_dialog.ExitConfirmDialog, "exec", fake_exec)

    assert logout_dialog.confirm_exit(parent) is True

    assert captured
    dialog_center = captured[0].geometry().center()
    parent_center = parent.geometry().center()
    assert abs(dialog_center.x() - parent_center.x()) <= 2
    assert abs(dialog_center.y() - parent_center.y()) <= 2


def test_logout_dialog_centers_on_parent(qtbot: Any, qapp: Any, monkeypatch: Any) -> None:
    from app.ui.widgets import logout_dialog

    parent = _parent_widget(qtbot, qapp)
    captured: list[QDialog] = []

    def fake_exec(self: QDialog) -> QDialog.DialogCode:
        captured.append(self)
        self.close()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(logout_dialog.LogoutConfirmDialog, "exec", fake_exec)

    assert logout_dialog.confirm_logout(parent) is True

    assert captured
    dialog_center = captured[0].geometry().center()
    parent_center = parent.geometry().center()
    assert abs(dialog_center.x() - parent_center.x()) <= 2
    assert abs(dialog_center.y() - parent_center.y()) <= 2
