"""Sticky EMZ footer with validation status and save action."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from app.ui.widgets.button_utils import compact_button


class EmzSaveFooter(QWidget):
    save_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("emzSaveFooter")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        self.status_label = QLabel("")
        self.status_label.setObjectName("emzSaveFooterStatus")
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.save_btn = QPushButton("Сохранить ЭМЗ")
        self.save_btn.setObjectName("primaryButton")
        compact_button(self.save_btn, min_width=140, max_width=220)
        self.save_btn.clicked.connect(self.save_requested.emit)
        layout.addWidget(self.save_btn)

    def set_state(self, *, missing_required: int, save_label: str, enabled: bool = True) -> None:
        if missing_required > 0:
            self.status_label.setText(f"Не заполнено обязательных полей: {missing_required}")
            self.status_label.setProperty("hasError", True)
        else:
            self.status_label.setText("")
            self.status_label.setProperty("hasError", False)

        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.save_btn.setText(save_label)
        self.save_btn.setEnabled(missing_required == 0 and enabled)
