"""Inline button for deleting a table row."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QTableWidget, QWidget


class RowDeleteButton(QPushButton):
    def __init__(self, table: QTableWidget, parent: QWidget | None = None) -> None:
        super().__init__("✕", parent)
        self.setObjectName("emzRowDeleteButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(24, 24)
        self.setToolTip("Удалить строку")
        self._table = table
        self.clicked.connect(self._delete_my_row)

    def _delete_my_row(self) -> None:
        last_col = self._table.columnCount() - 1
        for row in range(self._table.rowCount()):
            if self._table.cellWidget(row, last_col) is self:
                self._table.removeRow(row)
                return
