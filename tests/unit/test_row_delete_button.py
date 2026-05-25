from __future__ import annotations

from typing import Any

import pytest
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from app.ui.emz.widgets.row_delete_button import RowDeleteButton


@pytest.fixture
def table(qtbot: Any) -> QTableWidget:
    widget = QTableWidget(3, 4)
    qtbot.addWidget(widget)
    for row in range(3):
        for col in range(3):
            widget.setItem(row, col, QTableWidgetItem(f"r{row}c{col}"))
        widget.setCellWidget(row, 3, RowDeleteButton(widget))
    return widget


def test_deletes_middle_row(table: QTableWidget) -> None:
    button = table.cellWidget(1, 3)
    assert isinstance(button, RowDeleteButton)

    button.click()

    assert table.rowCount() == 2
    assert table.item(0, 0).text() == "r0c0"
    assert table.item(1, 0).text() == "r2c0"


def test_deletes_first_row(table: QTableWidget) -> None:
    button = table.cellWidget(0, 3)
    assert isinstance(button, RowDeleteButton)

    button.click()

    assert table.rowCount() == 2
    assert table.item(0, 0).text() == "r1c0"


def test_deletes_last_row(table: QTableWidget) -> None:
    button = table.cellWidget(2, 3)
    assert isinstance(button, RowDeleteButton)

    button.click()

    assert table.rowCount() == 2
    assert table.item(1, 0).text() == "r1c0"


def test_button_shows_text(table: QTableWidget) -> None:
    button = table.cellWidget(0, 3)
    assert isinstance(button, RowDeleteButton)

    assert button.text() == "Удалить"
    assert button.objectName() == "emzRowDeleteButton"
    assert button.focusPolicy().name == "NoFocus"
