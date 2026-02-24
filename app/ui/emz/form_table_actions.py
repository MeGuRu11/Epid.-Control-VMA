from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QComboBox, QDateEdit, QDateTimeEdit, QTableWidget

CreateComboFn = Callable[[], QComboBox]
CreateDateTimeEditFn = Callable[[], QDateTimeEdit]
CreateDateEditFn = Callable[[], QDateEdit]
ConnectComboResizeFn = Callable[[QTableWidget, QComboBox, int], None]


def add_diagnosis_row(
    *,
    table: QTableWidget,
    create_type_combo: CreateComboFn,
    create_icd_combo: CreateComboFn,
    connect_combo_resize: ConnectComboResizeFn,
) -> None:
    row = table.rowCount()
    table.insertRow(row)
    type_combo = create_type_combo()
    table.setCellWidget(row, 0, type_combo)
    connect_combo_resize(table, type_combo, row)
    icd_combo = create_icd_combo()
    table.setCellWidget(row, 1, icd_combo)
    connect_combo_resize(table, icd_combo, row)


def add_intervention_row(
    *,
    table: QTableWidget,
    create_type_combo: CreateComboFn,
    create_dt_cell: CreateDateTimeEditFn,
    connect_combo_resize: ConnectComboResizeFn,
) -> None:
    row = table.rowCount()
    table.insertRow(row)
    type_combo = create_type_combo()
    table.setCellWidget(row, 0, type_combo)
    connect_combo_resize(table, type_combo, row)
    table.setCellWidget(row, 1, create_dt_cell())
    table.setCellWidget(row, 2, create_dt_cell())


def add_abx_row(
    *,
    table: QTableWidget,
    create_dt_cell: CreateDateTimeEditFn,
    create_abx_combo: CreateComboFn,
    connect_combo_resize: ConnectComboResizeFn,
) -> None:
    row = table.rowCount()
    table.insertRow(row)
    table.setCellWidget(row, 0, create_dt_cell())
    table.setCellWidget(row, 1, create_dt_cell())
    combo = create_abx_combo()
    table.setCellWidget(row, 2, combo)
    connect_combo_resize(table, combo, row)


def add_ismp_row(
    *,
    table: QTableWidget,
    create_type_combo: CreateComboFn,
    create_date_cell: CreateDateEditFn,
    connect_combo_resize: ConnectComboResizeFn,
) -> None:
    row = table.rowCount()
    table.insertRow(row)
    type_combo = create_type_combo()
    table.setCellWidget(row, 0, type_combo)
    connect_combo_resize(table, type_combo, row)
    table.setCellWidget(row, 1, create_date_cell())


def delete_table_row(table: QTableWidget) -> None:
    if table.rowCount() <= 1:
        return
    row = table.currentRow()
    if row < 0:
        row = table.rowCount() - 1
    table.removeRow(row)
