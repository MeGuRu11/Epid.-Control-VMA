from __future__ import annotations

from collections.abc import Callable
from typing import cast

from PySide6.QtWidgets import QComboBox, QDateEdit, QDateTimeEdit, QTableWidget

from app.ui.widgets.table_utils import connect_combo_resize_on_first_row

CreateComboFn = Callable[[], QComboBox]
CreateDateEditFn = Callable[[], QDateEdit]
CreateDateTimeEditFn = Callable[[], QDateTimeEdit]
ResizeTableFn = Callable[[QTableWidget], None]


def setup_diagnosis_rows(
    *,
    table: QTableWidget,
    create_type_combo: CreateComboFn,
    create_icd_combo: CreateComboFn,
    resize_table: ResizeTableFn,
) -> None:
    for row in range(table.rowCount()):
        type_combo = create_type_combo()
        table.setCellWidget(row, 0, type_combo)
        connect_combo_resize_on_first_row(table, type_combo, row)
        icd_combo = create_icd_combo()
        table.setCellWidget(row, 1, icd_combo)
        connect_combo_resize_on_first_row(table, icd_combo, row)
    resize_table(table)


def setup_abx_rows(
    *,
    table: QTableWidget,
    create_dt_cell: CreateDateTimeEditFn,
    create_abx_combo: CreateComboFn,
    resize_table: ResizeTableFn,
) -> None:
    for row in range(table.rowCount()):
        if not isinstance(table.cellWidget(row, 0), QDateTimeEdit):
            table.setCellWidget(row, 0, create_dt_cell())
        if not isinstance(table.cellWidget(row, 1), QDateTimeEdit):
            table.setCellWidget(row, 1, create_dt_cell())
        abx_combo = create_abx_combo()
        table.setCellWidget(row, 2, abx_combo)
        connect_combo_resize_on_first_row(table, abx_combo, row)
    resize_table(table)


def setup_intervention_rows(
    *,
    table: QTableWidget,
    create_type_combo: CreateComboFn,
    create_dt_cell: CreateDateTimeEditFn,
    resize_table: ResizeTableFn,
) -> None:
    for row in range(table.rowCount()):
        if not isinstance(table.cellWidget(row, 0), QComboBox):
            type_combo = create_type_combo()
            table.setCellWidget(row, 0, type_combo)
            connect_combo_resize_on_first_row(table, type_combo, row)
        if not isinstance(table.cellWidget(row, 1), QDateTimeEdit):
            table.setCellWidget(row, 1, create_dt_cell())
        if not isinstance(table.cellWidget(row, 2), QDateTimeEdit):
            table.setCellWidget(row, 2, create_dt_cell())
    resize_table(table)


def setup_ismp_rows(
    *,
    table: QTableWidget,
    create_type_combo: CreateComboFn,
    create_date_cell: CreateDateEditFn,
    resize_table: ResizeTableFn,
) -> None:
    for row in range(table.rowCount()):
        if not isinstance(table.cellWidget(row, 0), QComboBox):
            type_combo = create_type_combo()
            table.setCellWidget(row, 0, type_combo)
            connect_combo_resize_on_first_row(table, type_combo, row)
        if not isinstance(table.cellWidget(row, 1), QDateEdit):
            table.setCellWidget(row, 1, create_date_cell())
    resize_table(table)


def refresh_diagnosis_reference_rows(
    *,
    table: QTableWidget,
    create_type_combo: CreateComboFn,
    create_icd_combo: CreateComboFn,
) -> None:
    for row in range(table.rowCount()):
        type_widget = table.cellWidget(row, 0)
        type_combo = cast(QComboBox, type_widget) if isinstance(type_widget, QComboBox) else None
        selected_type = type_combo.currentText() if type_combo else "Поступление"
        new_type_combo = create_type_combo()
        new_type_combo.setCurrentText(selected_type)
        table.setCellWidget(row, 0, new_type_combo)
        connect_combo_resize_on_first_row(table, new_type_combo, row)

        icd_widget = table.cellWidget(row, 1)
        icd_combo = cast(QComboBox, icd_widget) if isinstance(icd_widget, QComboBox) else None
        selected_icd = icd_combo.currentData() if icd_combo else None
        new_icd_combo = create_icd_combo()
        if selected_icd is not None:
            idx = new_icd_combo.findData(selected_icd)
            if idx >= 0:
                new_icd_combo.setCurrentIndex(idx)
        table.setCellWidget(row, 1, new_icd_combo)
        connect_combo_resize_on_first_row(table, new_icd_combo, row)


def refresh_abx_reference_rows(
    *,
    table: QTableWidget,
    create_abx_combo: CreateComboFn,
) -> None:
    for row in range(table.rowCount()):
        abx_widget = table.cellWidget(row, 2)
        abx_combo = cast(QComboBox, abx_widget) if isinstance(abx_widget, QComboBox) else None
        selected_abx = abx_combo.currentData() if abx_combo else None
        new_abx_combo = create_abx_combo()
        if selected_abx is not None:
            idx = new_abx_combo.findData(selected_abx)
            if idx >= 0:
                new_abx_combo.setCurrentIndex(idx)
        table.setCellWidget(row, 2, new_abx_combo)
        connect_combo_resize_on_first_row(table, new_abx_combo, row)


def refresh_ismp_reference_rows(
    *,
    table: QTableWidget,
    create_type_combo: CreateComboFn,
) -> None:
    for row in range(table.rowCount()):
        type_widget = table.cellWidget(row, 0)
        type_combo = cast(QComboBox, type_widget) if isinstance(type_widget, QComboBox) else None
        selected_type = cast(str | None, type_combo.currentData()) if type_combo else None
        new_type_combo = create_type_combo()
        if selected_type is not None:
            idx = new_type_combo.findData(selected_type)
            if idx >= 0:
                new_type_combo.setCurrentIndex(idx)
        table.setCellWidget(row, 0, new_type_combo)
        connect_combo_resize_on_first_row(table, new_type_combo, row)
