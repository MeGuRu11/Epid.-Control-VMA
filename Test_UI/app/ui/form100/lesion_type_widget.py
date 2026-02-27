from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QPushButton, QWidget


class LesionTypeWidget(QWidget):
    valuesChanged = Signal()

    def __init__(self, items: Iterable[tuple[str, str]], parent=None):
        super().__init__(parent)
        self._checks: dict[str, QPushButton] = {}
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(6)
        for idx, (key, title) in enumerate(items):
            btn = QPushButton(title)
            btn.setCheckable(True)
            btn.setObjectName("lesionToggle")
            btn.toggled.connect(lambda checked, b=btn: self._sync_button_state(b, checked))
            btn.toggled.connect(self.valuesChanged.emit)
            self._checks[key] = btn
            layout.addWidget(btn, idx // 2, idx % 2)

    def set_values(self, values: set[str]) -> None:
        for key, btn in self._checks.items():
            btn.setChecked(key in values)
            self._sync_button_state(btn, btn.isChecked())

    def values(self) -> set[str]:
        return {key for key, btn in self._checks.items() if btn.isChecked()}

    def set_enabled(self, enabled: bool) -> None:
        for btn in self._checks.values():
            btn.setEnabled(enabled)

    @staticmethod
    def _sync_button_state(btn: QPushButton, checked: bool) -> None:
        btn.setProperty("active", bool(checked))
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        btn.update()

    @property
    def checks(self) -> dict[str, QPushButton]:
        return self._checks
