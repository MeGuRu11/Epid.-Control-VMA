from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QTableWidget


def resize_columns_by_first_row(
    table: QTableWidget, *, min_width: int = 80, padding: int = 24
) -> None:
    if table.columnCount() == 0:
        return
    metrics = table.fontMetrics()
    first_row = 0 if table.rowCount() > 0 else None
    min_widths = table.property("min_column_widths")
    col_min_map = min_widths if isinstance(min_widths, dict) else {}
    for col in range(table.columnCount()):
        header_item = table.horizontalHeaderItem(col)
        header_text = header_item.text() if header_item else ""
        header_width = metrics.horizontalAdvance(header_text)

        cell_width = 0
        if first_row is not None:
            item = table.item(first_row, col)
            if item and item.text():
                cell_width = metrics.horizontalAdvance(item.text())
            else:
                widget = table.cellWidget(first_row, col)
                if widget is not None and hasattr(widget, "currentText"):
                    text = widget.currentText()
                    cell_width = metrics.horizontalAdvance(text)

        col_min_width = col_min_map.get(col, min_width)
        width = max(header_width, cell_width, col_min_width) + padding
        table.setColumnWidth(col, width)


def connect_combo_autowidth(
    combo: QComboBox, *, min_width: int = 80, padding: int = 24
) -> None:
    def _update_width() -> None:
        text = combo.currentText() or ""
        width = combo.fontMetrics().horizontalAdvance(text) + padding
        combo.setMinimumWidth(max(min_width, width))

    combo.currentIndexChanged.connect(lambda _index: _update_width())
    if combo.isEditable():
        combo.editTextChanged.connect(lambda _text: _update_width())
    _update_width()


def connect_combo_resize_on_first_row(
    table: QTableWidget, combo: QComboBox, row: int
) -> None:
    if row != 0:
        return

    def _on_change(_index: int) -> None:
        resize_columns_by_first_row(table)

    combo.currentIndexChanged.connect(_on_change)
