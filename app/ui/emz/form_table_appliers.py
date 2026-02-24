from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import cast

from PySide6.QtCore import QDate, QDateTime
from PySide6.QtWidgets import QComboBox, QDateEdit, QDateTimeEdit, QTableWidget, QTableWidgetItem

from app.application.dto.emz_dto import (
    EmzAntibioticCourseDto,
    EmzDiagnosisDto,
    EmzInterventionDto,
    EmzIsmpDto,
)
from app.ui.emz.form_utils import diagnosis_kind_to_ui
from app.ui.widgets.table_utils import connect_combo_resize_on_first_row

PrepareTableFn = Callable[[QTableWidget, int], None]
ResizeTableFn = Callable[[QTableWidget], None]
SetupRowsFn = Callable[[], None]
CreateComboFn = Callable[[], QComboBox]
CreateDateEditFn = Callable[[], QDateEdit]
CreateDateTimeEditFn = Callable[[], QDateTimeEdit]
ToQDateFn = Callable[[date], QDate]
ToQDateTimeFn = Callable[[datetime], QDateTime]


def apply_diagnosis_rows(
    *,
    table: QTableWidget,
    items: list[EmzDiagnosisDto],
    prepare_table: PrepareTableFn,
    setup_rows: SetupRowsFn,
    resize_table: ResizeTableFn,
) -> None:
    prepare_table(table, len(items))
    setup_rows()
    for row, diagnosis in enumerate(items):
        type_widget = table.cellWidget(row, 0)
        type_combo = cast(QComboBox, type_widget) if isinstance(type_widget, QComboBox) else None
        if type_combo:
            type_combo.setCurrentText(diagnosis_kind_to_ui(diagnosis.kind))
        combo_widget = table.cellWidget(row, 1)
        combo = cast(QComboBox, combo_widget) if isinstance(combo_widget, QComboBox) else None
        if combo:
            combo.setCurrentIndex(combo.findData(diagnosis.icd10_code))
        table.setItem(row, 2, QTableWidgetItem(diagnosis.free_text or ""))
    resize_table(table)


def apply_intervention_rows(
    *,
    table: QTableWidget,
    items: list[EmzInterventionDto],
    prepare_table: PrepareTableFn,
    resize_table: ResizeTableFn,
    create_type_combo: CreateComboFn,
    create_dt_cell: CreateDateTimeEditFn,
    to_qdatetime: ToQDateTimeFn,
) -> None:
    prepare_table(table, len(items))
    for row, intervention in enumerate(items):
        type_combo = create_type_combo()
        type_combo.setCurrentText(intervention.type)
        table.setCellWidget(row, 0, type_combo)
        connect_combo_resize_on_first_row(table, type_combo, row)

        start_widget = create_dt_cell()
        if intervention.start_dt:
            start_widget.setDateTime(to_qdatetime(intervention.start_dt))
        table.setCellWidget(row, 1, start_widget)

        end_widget = create_dt_cell()
        if intervention.end_dt:
            end_widget.setDateTime(to_qdatetime(intervention.end_dt))
        table.setCellWidget(row, 2, end_widget)

        table.setItem(
            row,
            3,
            QTableWidgetItem(str(intervention.duration_minutes) if intervention.duration_minutes else ""),
        )
        table.setItem(row, 4, QTableWidgetItem(intervention.performed_by or ""))
        table.setItem(row, 5, QTableWidgetItem(intervention.notes or ""))
    resize_table(table)


def apply_abx_rows(
    *,
    table: QTableWidget,
    items: list[EmzAntibioticCourseDto],
    prepare_table: PrepareTableFn,
    setup_rows: SetupRowsFn,
    resize_table: ResizeTableFn,
    create_dt_cell: CreateDateTimeEditFn,
    to_qdatetime: ToQDateTimeFn,
) -> None:
    prepare_table(table, len(items))
    setup_rows()
    for row, course in enumerate(items):
        start_widget = create_dt_cell()
        if course.start_dt:
            start_widget.setDateTime(to_qdatetime(course.start_dt))
        table.setCellWidget(row, 0, start_widget)

        end_widget = create_dt_cell()
        if course.end_dt:
            end_widget.setDateTime(to_qdatetime(course.end_dt))
        table.setCellWidget(row, 1, end_widget)

        combo_widget = table.cellWidget(row, 2)
        combo = cast(QComboBox, combo_widget) if isinstance(combo_widget, QComboBox) else None
        if combo:
            combo.setCurrentIndex(combo.findData(course.antibiotic_id))
        table.setItem(row, 3, QTableWidgetItem(course.drug_name_free or ""))
        table.setItem(row, 4, QTableWidgetItem(course.route or ""))
    resize_table(table)


def apply_ismp_rows(
    *,
    table: QTableWidget,
    items: list[EmzIsmpDto],
    prepare_table: PrepareTableFn,
    setup_rows: SetupRowsFn,
    resize_table: ResizeTableFn,
    create_type_combo: CreateComboFn,
    create_date_cell: CreateDateEditFn,
    to_qdate: ToQDateFn,
) -> None:
    prepare_table(table, len(items))
    setup_rows()
    for row, item in enumerate(items):
        type_widget = create_type_combo()
        type_widget.setCurrentIndex(type_widget.findData(item.ismp_type))
        table.setCellWidget(row, 0, type_widget)
        connect_combo_resize_on_first_row(table, type_widget, row)

        date_widget = create_date_cell()
        date_widget.setDate(to_qdate(item.start_date))
        table.setCellWidget(row, 1, date_widget)
    resize_table(table)
