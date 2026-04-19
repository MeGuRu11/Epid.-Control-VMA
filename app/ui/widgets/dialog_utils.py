from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractButton,
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QWidget,
)

_MESSAGE_BUTTON_TEXTS: tuple[tuple[QMessageBox.StandardButton, str], ...] = (
    (QMessageBox.StandardButton.Yes, "Да"),
    (QMessageBox.StandardButton.No, "Нет"),
    (QMessageBox.StandardButton.Ok, "ОК"),
    (QMessageBox.StandardButton.Save, "Сохранить"),
    (QMessageBox.StandardButton.Cancel, "Отмена"),
    (QMessageBox.StandardButton.Close, "Закрыть"),
)

_BUTTON_BOX_TEXTS: tuple[tuple[QDialogButtonBox.StandardButton, str], ...] = (
    (QDialogButtonBox.StandardButton.Yes, "Да"),
    (QDialogButtonBox.StandardButton.No, "Нет"),
    (QDialogButtonBox.StandardButton.Ok, "ОК"),
    (QDialogButtonBox.StandardButton.Save, "Сохранить"),
    (QDialogButtonBox.StandardButton.Cancel, "Отмена"),
    (QDialogButtonBox.StandardButton.Close, "Закрыть"),
)


def _set_button_text(button: QAbstractButton | None, text: str) -> None:
    if button is not None:
        button.setText(text)


def localize_message_box_buttons(box: QMessageBox) -> QMessageBox:
    """Применить русские подписи к стандартным кнопкам QMessageBox."""
    for standard_button, text in _MESSAGE_BUTTON_TEXTS:
        _set_button_text(box.button(standard_button), text)
    return box


def localize_button_box(button_box: QDialogButtonBox) -> QDialogButtonBox:
    """Применить русские подписи к стандартным кнопкам QDialogButtonBox."""
    for standard_button, text in _BUTTON_BOX_TEXTS:
        _set_button_text(button_box.button(standard_button), text)
    return button_box


def localize_input_dialog_buttons(dialog: QInputDialog) -> QInputDialog:
    """Применить русские подписи к стандартным кнопкам QInputDialog."""

    def _apply() -> None:
        button_box = dialog.findChild(QDialogButtonBox)
        if button_box is not None:
            localize_button_box(button_box)

    _apply()
    QTimer.singleShot(0, _apply)
    return dialog


def exec_text_input_dialog(
    parent: QWidget | None,
    title: str,
    label: str,
    *,
    text: str = "",
    echo_mode: QLineEdit.EchoMode = QLineEdit.EchoMode.Normal,
) -> tuple[str, bool]:
    """Показать QInputDialog с русскими стандартными кнопками."""
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextValue(text)
    dialog.setTextEchoMode(echo_mode)
    localize_input_dialog_buttons(dialog)
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    return dialog.textValue(), accepted


def exec_message_box(
    parent: QWidget | None,
    title: str,
    text: str,
    *,
    icon: QMessageBox.Icon = QMessageBox.Icon.Information,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton | None = None,
    informative_text: str = "",
    detailed_text: str = "",
) -> QMessageBox.StandardButton:
    """Показать QMessageBox с русскими стандартными кнопками."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(icon)
    box.setStandardButtons(buttons)
    if default_button is not None:
        box.setDefaultButton(default_button)
    if informative_text:
        box.setInformativeText(informative_text)
    if detailed_text:
        box.setDetailedText(detailed_text)
    localize_message_box_buttons(box)
    box.exec()
    clicked = box.clickedButton()
    if clicked is None:
        return default_button or QMessageBox.StandardButton.NoButton
    return box.standardButton(clicked)
