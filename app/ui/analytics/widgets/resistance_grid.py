from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QWidget

from app.ui.widgets.table_utils import set_table_read_only


class ResistanceGrid(QTableWidget):
    """Матрица «Микроорганизмы × Антибиотики» с долей R."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, 0, parent)
        self.setAlternatingRowColors(False)
        set_table_read_only(self)

    def set_data(self, data: dict[str, dict[str, dict[str, int]]]) -> None:
        self.clearContents()
        if not data:
            self.setRowCount(0)
            self.setColumnCount(0)
            return

        micros = list(data.keys())
        antibiotics: list[str] = []
        for abx_map in data.values():
            for antibiotic in abx_map:
                if antibiotic not in antibiotics:
                    antibiotics.append(antibiotic)

        self.setRowCount(len(micros))
        self.setColumnCount(len(antibiotics))
        self.setVerticalHeaderLabels([self._short_label(micro, 20) for micro in micros])
        self.setHorizontalHeaderLabels([self._short_label(antibiotic, 10) for antibiotic in antibiotics])

        for row, micro in enumerate(micros):
            for column, antibiotic in enumerate(antibiotics):
                cell = data[micro].get(antibiotic, {"S": 0, "I": 0, "R": 0, "total": 0})
                self.setItem(row, column, self._item_for_cell(cell))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def _item_for_cell(self, cell: dict[str, int]) -> QTableWidgetItem:
        total = cell.get("total", 0)
        if total < 5:
            item = QTableWidgetItem("\u2014")
            item.setForeground(QColor("#AAAAAA"))
            return item

        resistant_percent = cell.get("R", 0) / total * 100
        item = QTableWidgetItem(f"{resistant_percent:.0f}%")
        if resistant_percent >= 50:
            item.setBackground(QColor("#FECACA"))
            item.setForeground(QColor("#991B1B"))
        elif resistant_percent >= 20:
            item.setBackground(QColor("#FEF3C7"))
            item.setForeground(QColor("#92400E"))
        else:
            item.setBackground(QColor("#EAF3DE"))
            item.setForeground(QColor("#3B6D11"))
        return item

    def _short_label(self, value: str, limit: int) -> str:
        tail = value.split(" - ")[-1]
        return tail if len(tail) <= limit else f"{tail[: limit - 1]}…"
