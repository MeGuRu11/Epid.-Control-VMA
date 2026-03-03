from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget


class ValidationBanner(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWordWrap(True)
        self.setObjectName("validationBanner")
        self.hide()

    def show_error(self, text: str) -> None:
        self.setText(text)
        self.show()

    def clear_error(self) -> None:
        self.clear()
        self.hide()
