from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class EmptyState(QWidget):
    """Плашка «нет данных» для вкладок Analytics v2."""

    def __init__(
        self,
        message: str = "Нет данных за выбранный период.",
        hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        frame = QFrame()
        frame.setObjectName("emptyState")

        msg_label = QLabel(message)
        msg_label.setObjectName("emptyStateText")
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_label.setWordWrap(True)

        inner = QVBoxLayout(frame)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(msg_label)

        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("emptyStateHint")
            hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint_label.setWordWrap(True)
            inner.addWidget(hint_label)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 16, 0, 16)
        root.addWidget(frame)
