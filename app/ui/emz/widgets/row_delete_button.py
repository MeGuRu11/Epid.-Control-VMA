"""Inline-кнопка удаления строки таблицы."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QTableWidget, QWidget

from app.ui.widgets.button_utils import compact_button


class RowDeleteButton(QPushButton):
    """Кнопка 'Удалить' в строке таблицы."""

    def __init__(self, table: QTableWidget, parent: QWidget | None = None) -> None:
        super().__init__("Удалить", parent)
        self.setObjectName("emzRowDeleteButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        compact_button(self, min_width=80, max_width=100)
        self._table = table
        self.clicked.connect(self._delete_my_row)

    def _delete_my_row(self) -> None:
        last_col = self._table.columnCount() - 1
        for row in range(self._table.rowCount()):
            if self._table.cellWidget(row, last_col) is self:
                self._table.removeRow(row)
                return
