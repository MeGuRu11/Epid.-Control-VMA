from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class IconSelectWidget(QWidget):
    valueChanged = Signal(str)

    def __init__(self, items: Iterable[tuple[str, str]], parent=None):
        super().__init__(parent)
        self._buttons: dict[str, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for value, title in items:
            btn = QPushButton(title)
            btn.setCheckable(True)
            btn.setObjectName("iconSelectToggle")
            btn.clicked.connect(lambda checked, key=value: self._on_clicked(key, checked))
            self._buttons[value] = btn
            layout.addWidget(btn)

        layout.addStretch(1)

    def set_value(self, value: str) -> None:
        for key, btn in self._buttons.items():
            checked = key == value
            btn.setChecked(checked)
            self._sync_button_style(btn, checked)

    def value(self) -> str:
        for key, btn in self._buttons.items():
            if btn.isChecked():
                return key
        return ""

    def clear_value(self) -> None:
        for btn in self._buttons.values():
            btn.setChecked(False)
            self._sync_button_style(btn, False)
        self.valueChanged.emit("")

    def _on_clicked(self, key: str, checked: bool) -> None:
        if checked:
            for item_key, btn in self._buttons.items():
                if item_key != key:
                    btn.setChecked(False)
                    self._sync_button_style(btn, False)
            self._sync_button_style(self._buttons[key], True)
        else:
            self._sync_button_style(self._buttons[key], False)
        self.valueChanged.emit(self.value())

    @staticmethod
    def _sync_button_style(btn: QPushButton, checked: bool) -> None:
        btn.setProperty("active", bool(checked))
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        btn.update()
