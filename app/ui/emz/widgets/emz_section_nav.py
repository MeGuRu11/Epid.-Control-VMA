"""Sticky chip navigation for EMZ sections with counters."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class EmzSectionNavBar(QWidget):
    navigate_requested = Signal(str)

    SECTIONS = [
        ("patient", "Основное"),
        ("diagnoses", "Диагнозы"),
        ("interventions", "Вмешательства"),
        ("antibiotics", "Антибиотики"),
        ("ismp", "ИСМП"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("emzSectionNavBar")
        self._chips: dict[str, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(6)
        for anchor, title in self.SECTIONS:
            chip = QPushButton(title)
            chip.setObjectName("emzSectionChip")
            chip.setFlat(True)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda _checked=False, a=anchor: self.navigate_requested.emit(a))
            self._chips[anchor] = chip
            layout.addWidget(chip)
        layout.addStretch()

    def update_counts(self, counts: dict[str, int]) -> None:
        for anchor, title in self.SECTIONS:
            count = counts.get(anchor, 0)
            chip = self._chips[anchor]
            if anchor == "patient":
                chip.setText(f"{title} ({count} незап.)" if count > 0 else title)
                chip.setProperty("hasError", count > 0)
            else:
                chip.setText(f"{title} ({count})" if count > 0 else title)
                chip.setProperty("hasError", False)
            chip.style().unpolish(chip)
            chip.style().polish(chip)
