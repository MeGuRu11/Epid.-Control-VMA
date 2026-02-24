from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QWidget


class FlagsStrip(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.flag_urgent = QCheckBox("Срочно")
        self.flag_sanitation = QCheckBox("Санобработка")
        self.flag_isolation = QCheckBox("Изоляция")
        self.flag_radiation = QCheckBox("Радиация")
        layout.addWidget(self.flag_urgent)
        layout.addWidget(self.flag_sanitation)
        layout.addWidget(self.flag_isolation)
        layout.addWidget(self.flag_radiation)
        layout.addStretch()

    def get_values(self) -> dict[str, bool]:
        return {
            "flag_urgent": self.flag_urgent.isChecked(),
            "flag_sanitation": self.flag_sanitation.isChecked(),
            "flag_isolation": self.flag_isolation.isChecked(),
            "flag_radiation": self.flag_radiation.isChecked(),
        }

    def set_values(self, values: dict[str, bool]) -> None:
        self.flag_urgent.setChecked(bool(values.get("flag_urgent")))
        self.flag_sanitation.setChecked(bool(values.get("flag_sanitation")))
        self.flag_isolation.setChecked(bool(values.get("flag_isolation")))
        self.flag_radiation.setChecked(bool(values.get("flag_radiation")))
