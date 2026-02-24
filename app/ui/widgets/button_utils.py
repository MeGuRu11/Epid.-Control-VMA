from __future__ import annotations

from PySide6.QtWidgets import QPushButton


def compact_button(button: QPushButton, min_width: int = 104, max_width: int = 200) -> QPushButton:
    button.setMinimumWidth(min_width)
    button.setMaximumWidth(max_width)
    return button
