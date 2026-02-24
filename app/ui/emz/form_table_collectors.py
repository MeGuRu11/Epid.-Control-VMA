from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import cast

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QComboBox, QDateEdit, QTableWidget

from app.application.dto.emz_dto import (
    EmzAntibioticCourseDto,
    EmzDiagnosisDto,
    EmzInterventionDto,
    EmzIsmpDto,
)
from app.ui.emz.form_mappers import (
    map_antibiotic_course,
    map_diagnosis,
    map_intervention,
    map_ismp_case,
)

TableDtResolver = Callable[[QTableWidget, int, int], datetime | None]


def collect_diagnoses(*, table: QTableWidget) -> list[EmzDiagnosisDto]:
    items: list[EmzDiagnosisDto] = []
    for row in range(table.rowCount()):
        type_widget = table.cellWidget(row, 0)
        type_combo = cast(QComboBox, type_widget) if isinstance(type_widget, QComboBox) else None
        kind_item = table.item(row, 0)
        icd_widget = table.cellWidget(row, 1)
        icd_combo = cast(QComboBox, icd_widget) if isinstance(icd_widget, QComboBox) else None
        text_item = table.item(row, 2)
        raw_kind = ""
        if type_combo and type_combo.currentText():
            raw_kind = type_combo.currentText().strip().lower()
        elif kind_item and kind_item.text():
            raw_kind = kind_item.text().strip().lower()
        icd_code = icd_combo.currentData() if icd_combo else None
        free_text = text_item.text() if text_item else None
        dto = map_diagnosis(raw_kind=raw_kind, icd_code=icd_code, free_text=free_text)
        if dto is not None:
            items.append(dto)
    return items


def collect_interventions(*, table: QTableWidget, dt_resolver: TableDtResolver) -> list[EmzInterventionDto]:
    items: list[EmzInterventionDto] = []
    for row in range(table.rowCount()):
        type_widget = table.cellWidget(row, 0)
        type_combo = cast(QComboBox, type_widget) if isinstance(type_widget, QComboBox) else None
        type_item = table.item(row, 0)
        type_value = type_combo.currentText().strip() if type_combo else (type_item.text().strip() if type_item else "")
        if not type_value:
            continue
        start_dt = dt_resolver(table, row, 1)
        end_dt = dt_resolver(table, row, 2)
        duration_item = table.item(row, 3)
        performed_item = table.item(row, 4)
        notes_item = table.item(row, 5)
        dto = map_intervention(
            type_value=type_value,
            start_dt=start_dt,
            end_dt=end_dt,
            duration_text=duration_item.text() if duration_item else None,
            performed_by=performed_item.text() if performed_item else None,
            notes=notes_item.text() if notes_item else None,
        )
        if dto is not None:
            items.append(dto)
    return items


def collect_abx(*, table: QTableWidget, dt_resolver: TableDtResolver) -> list[EmzAntibioticCourseDto]:
    items: list[EmzAntibioticCourseDto] = []
    for row in range(table.rowCount()):
        start_dt = dt_resolver(table, row, 0)
        end_dt = dt_resolver(table, row, 1)
        abx_widget = table.cellWidget(row, 2)
        abx_combo = cast(QComboBox, abx_widget) if isinstance(abx_widget, QComboBox) else None
        free_item = table.item(row, 3)
        route_item = table.item(row, 4)
        abx_id = abx_combo.currentData() if abx_combo else None
        if abx_id or free_item:
            items.append(
                map_antibiotic_course(
                    start_dt=start_dt,
                    end_dt=end_dt,
                    antibiotic_id=abx_id,
                    drug_name_free=free_item.text() if free_item else None,
                    route=route_item.text() if route_item else None,
                )
            )
    return items


def collect_ismp(*, table: QTableWidget, date_empty: QDate) -> list[EmzIsmpDto]:
    items: list[EmzIsmpDto] = []
    for row in range(table.rowCount()):
        type_widget = table.cellWidget(row, 0)
        type_combo = cast(QComboBox, type_widget) if isinstance(type_widget, QComboBox) else None
        ismp_type = type_combo.currentData() if type_combo else None
        if not ismp_type:
            continue
        date_widget = table.cellWidget(row, 1)
        date_edit = cast(QDateEdit, date_widget) if isinstance(date_widget, QDateEdit) else None
        if not date_edit:
            continue
        qdate = date_edit.date()
        if qdate == date_empty:
            continue
        start_date = cast(date, qdate.toPython())
        dto = map_ismp_case(ismp_type=cast(str | None, ismp_type), start_date=start_date)
        if dto is not None:
            items.append(dto)
    return items
