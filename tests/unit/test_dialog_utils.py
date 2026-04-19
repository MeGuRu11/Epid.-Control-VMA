from __future__ import annotations

from PySide6.QtWidgets import QDialogButtonBox, QInputDialog

from app.ui.widgets.dialog_utils import localize_input_dialog_buttons


def test_localize_input_dialog_buttons_translates_standard_buttons(qapp) -> None:
    dialog = QInputDialog()
    dialog.setWindowTitle("Подпись")
    dialog.setLabelText("Подписант (разборчиво):")

    dialog.show()
    qapp.processEvents()
    localize_input_dialog_buttons(dialog)
    qapp.processEvents()

    button_box = dialog.findChild(QDialogButtonBox)

    assert button_box is not None
    assert button_box.button(QDialogButtonBox.StandardButton.Ok).text() == "ОК"
    assert button_box.button(QDialogButtonBox.StandardButton.Cancel).text() == "Отмена"

    dialog.close()
