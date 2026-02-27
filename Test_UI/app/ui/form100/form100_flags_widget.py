from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QWidget


class Form100FlagsWidget(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.flag_emergency = QCheckBox("Неотложная помощь")
        self.flag_radiation = QCheckBox("Радиационное поражение")
        self.flag_sanitation = QCheckBox("Санитарная обработка")

        self.flag_emergency.setObjectName("form100FlagEmergency")
        self.flag_radiation.setObjectName("form100FlagRadiation")
        self.flag_sanitation.setObjectName("form100FlagSanitation")

        self.flag_emergency.toggled.connect(self.changed.emit)
        self.flag_radiation.toggled.connect(self.changed.emit)
        self.flag_sanitation.toggled.connect(self.changed.emit)

        layout.addWidget(self.flag_emergency)
        layout.addWidget(self.flag_radiation)
        layout.addWidget(self.flag_sanitation)
        layout.addStretch(1)

    def set_values(self, payload: dict[str, str]) -> None:
        self.flag_emergency.setChecked(str(payload.get("flag_emergency") or "").lower() in {"1", "true", "yes", "on"})
        self.flag_radiation.setChecked(str(payload.get("flag_radiation") or "").lower() in {"1", "true", "yes", "on"})
        self.flag_sanitation.setChecked(str(payload.get("flag_sanitation") or "").lower() in {"1", "true", "yes", "on"})

    def collect(self) -> dict[str, str]:
        return {
            "flag_emergency": "1" if self.flag_emergency.isChecked() else "0",
            "flag_radiation": "1" if self.flag_radiation.isChecked() else "0",
            "flag_sanitation": "1" if self.flag_sanitation.isChecked() else "0",
        }

    def set_enabled(self, enabled: bool) -> None:
        self.flag_emergency.setEnabled(enabled)
        self.flag_radiation.setEnabled(enabled)
        self.flag_sanitation.setEnabled(enabled)
