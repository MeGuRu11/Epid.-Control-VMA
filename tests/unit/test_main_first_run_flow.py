from __future__ import annotations

from PySide6.QtWidgets import QDialog

from app import main as app_main


class _AcceptedDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[str] = []

    def exec(self) -> QDialog.DialogCode:  # noqa: A003
        self.events.append("exec")
        self.show()
        return QDialog.DialogCode.Accepted

    def hide(self) -> None:
        self.events.append("hide")
        super().hide()

    def deleteLater(self) -> None:  # noqa: N802
        self.events.append("deleteLater")
        super().deleteLater()


def test_first_run_dialog_teardown_happens_before_startup_flow_continues(qapp) -> None:
    dialog = _AcceptedDialog()

    result = app_main._exec_first_run_dialog(dialog, qapp)

    assert result == QDialog.DialogCode.Accepted
    assert dialog.events == ["exec", "hide", "deleteLater"]
