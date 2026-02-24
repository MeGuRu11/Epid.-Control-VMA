from __future__ import annotations

from typing import cast

from PySide6.QtWidgets import QTableWidget

import app.ui.emz.form_table_actions as actions
from app.ui.emz.form_table_actions import (
    add_abx_row,
    add_diagnosis_row,
    add_intervention_row,
    add_ismp_row,
    delete_table_row,
)


class _FakeCombo:
    pass


class _FakeDateTimeEdit:
    pass


class _FakeDateEdit:
    pass


class _FakeTable:
    def __init__(self, row_count: int = 0, current_row: int = -1) -> None:
        self._row_count = row_count
        self._current_row = current_row
        self.widgets: dict[tuple[int, int], object] = {}
        self.removed_rows: list[int] = []

    def rowCount(self) -> int:  # noqa: N802
        return self._row_count

    def insertRow(self, row: int) -> None:  # noqa: N802
        assert row == self._row_count
        self._row_count += 1

    def setCellWidget(self, row: int, col: int, widget: object) -> None:  # noqa: N802
        self.widgets[(row, col)] = widget

    def cellWidget(self, row: int, col: int) -> object | None:  # noqa: N802
        return self.widgets.get((row, col))

    def currentRow(self) -> int:  # noqa: N802
        return self._current_row

    def removeRow(self, row: int) -> None:  # noqa: N802
        self.removed_rows.append(row)
        self._row_count -= 1


def test_add_diagnosis_row_inserts_and_connects() -> None:
    connected: list[tuple[int, object]] = []
    table = cast(QTableWidget, _FakeTable(row_count=1))

    def _connect(_table: QTableWidget, combo: _FakeCombo, row: int) -> None:
        connected.append((row, combo))

    add_diagnosis_row(
        table=table,
        create_type_combo=cast(actions.CreateComboFn, lambda: _FakeCombo()),
        create_icd_combo=cast(actions.CreateComboFn, lambda: _FakeCombo()),
        connect_combo_resize=cast(actions.ConnectComboResizeFn, _connect),
    )

    fake = cast(_FakeTable, table)
    assert fake.rowCount() == 2
    assert isinstance(fake.cellWidget(1, 0), _FakeCombo)
    assert isinstance(fake.cellWidget(1, 1), _FakeCombo)
    assert [row for row, _ in connected] == [1, 1]


def test_add_intervention_row_inserts_widgets() -> None:
    connected: list[int] = []
    table = cast(QTableWidget, _FakeTable(row_count=2))

    def _connect(_table: QTableWidget, _combo: _FakeCombo, row: int) -> None:
        connected.append(row)

    add_intervention_row(
        table=table,
        create_type_combo=cast(actions.CreateComboFn, lambda: _FakeCombo()),
        create_dt_cell=cast(actions.CreateDateTimeEditFn, lambda: _FakeDateTimeEdit()),
        connect_combo_resize=cast(actions.ConnectComboResizeFn, _connect),
    )

    fake = cast(_FakeTable, table)
    assert fake.rowCount() == 3
    assert isinstance(fake.cellWidget(2, 0), _FakeCombo)
    assert isinstance(fake.cellWidget(2, 1), _FakeDateTimeEdit)
    assert isinstance(fake.cellWidget(2, 2), _FakeDateTimeEdit)
    assert connected == [2]


def test_add_abx_row_inserts_widgets() -> None:
    connected: list[int] = []
    table = cast(QTableWidget, _FakeTable(row_count=0))

    def _connect(_table: QTableWidget, _combo: _FakeCombo, row: int) -> None:
        connected.append(row)

    add_abx_row(
        table=table,
        create_dt_cell=cast(actions.CreateDateTimeEditFn, lambda: _FakeDateTimeEdit()),
        create_abx_combo=cast(actions.CreateComboFn, lambda: _FakeCombo()),
        connect_combo_resize=cast(actions.ConnectComboResizeFn, _connect),
    )

    fake = cast(_FakeTable, table)
    assert fake.rowCount() == 1
    assert isinstance(fake.cellWidget(0, 0), _FakeDateTimeEdit)
    assert isinstance(fake.cellWidget(0, 1), _FakeDateTimeEdit)
    assert isinstance(fake.cellWidget(0, 2), _FakeCombo)
    assert connected == [0]


def test_add_ismp_row_inserts_widgets() -> None:
    connected: list[int] = []
    table = cast(QTableWidget, _FakeTable(row_count=3))

    def _connect(_table: QTableWidget, _combo: _FakeCombo, row: int) -> None:
        connected.append(row)

    add_ismp_row(
        table=table,
        create_type_combo=cast(actions.CreateComboFn, lambda: _FakeCombo()),
        create_date_cell=cast(actions.CreateDateEditFn, lambda: _FakeDateEdit()),
        connect_combo_resize=cast(actions.ConnectComboResizeFn, _connect),
    )

    fake = cast(_FakeTable, table)
    assert fake.rowCount() == 4
    assert isinstance(fake.cellWidget(3, 0), _FakeCombo)
    assert isinstance(fake.cellWidget(3, 1), _FakeDateEdit)
    assert connected == [3]


def test_delete_table_row_respects_minimum_one_row() -> None:
    table = cast(QTableWidget, _FakeTable(row_count=1, current_row=0))
    delete_table_row(table)
    fake = cast(_FakeTable, table)
    assert fake.rowCount() == 1
    assert fake.removed_rows == []


def test_delete_table_row_removes_last_when_current_missing() -> None:
    table = cast(QTableWidget, _FakeTable(row_count=4, current_row=-1))
    delete_table_row(table)
    fake = cast(_FakeTable, table)
    assert fake.removed_rows == [3]
    assert fake.rowCount() == 3


def test_delete_table_row_removes_selected_row() -> None:
    table = cast(QTableWidget, _FakeTable(row_count=4, current_row=1))
    delete_table_row(table)
    fake = cast(_FakeTable, table)
    assert fake.removed_rows == [1]
    assert fake.rowCount() == 3
