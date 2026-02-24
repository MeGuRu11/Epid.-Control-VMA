from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from PySide6.QtWidgets import QComboBox, QDateEdit, QDateTimeEdit, QTableWidget

from app.ui.emz.form_table_setups import (
    refresh_abx_reference_rows,
    refresh_diagnosis_reference_rows,
    refresh_ismp_reference_rows,
    setup_abx_rows,
    setup_diagnosis_rows,
    setup_intervention_rows,
    setup_ismp_rows,
)

CreateComboFn = Callable[[], QComboBox]
CreateDateTimeEditFn = Callable[[], QDateTimeEdit]
CreateDateEditFn = Callable[[], QDateEdit]
ResizeTableFn = Callable[[QTableWidget], None]
ConnectComboAutowidthFn = Callable[[QComboBox], None]


@dataclass(frozen=True)
class DetailReferenceLists:
    icd_items: Sequence[object]
    antibiotics: Sequence[object]
    ismp_abbreviations: Sequence[object]


def apply_departments_to_combo(
    *,
    department_combo: QComboBox,
    departments: Sequence[object],
    connect_combo_autowidth: ConnectComboAutowidthFn,
) -> None:
    department_combo.clear()
    department_combo.addItem("Выбрать", None)
    for dep in departments:
        dep_name = getattr(dep, "name", "")
        dep_id_raw: Any = getattr(dep, "id", None)
        dep_id = int(dep_id_raw) if dep_id_raw is not None else None
        department_combo.addItem(str(dep_name), dep_id)
    connect_combo_autowidth(department_combo)


def restore_department_selection(
    *,
    department_combo: QComboBox,
    current_department: object | None,
) -> None:
    if current_department is None:
        return
    idx = department_combo.findData(current_department)
    if idx >= 0:
        department_combo.setCurrentIndex(idx)


def setup_detail_reference_rows(
    *,
    diagnosis_table: QTableWidget,
    intervention_table: QTableWidget,
    abx_table: QTableWidget,
    ismp_table: QTableWidget,
    create_diag_type_combo: CreateComboFn,
    create_icd_combo: CreateComboFn,
    create_intervention_type_combo: CreateComboFn,
    create_dt_cell: CreateDateTimeEditFn,
    create_abx_combo: CreateComboFn,
    create_ismp_type_combo: CreateComboFn,
    create_date_cell: CreateDateEditFn,
    resize_table: ResizeTableFn,
) -> None:
    setup_diagnosis_reference_rows(
        diagnosis_table=diagnosis_table,
        create_diag_type_combo=create_diag_type_combo,
        create_icd_combo=create_icd_combo,
        resize_table=resize_table,
    )
    setup_intervention_rows(
        table=intervention_table,
        create_type_combo=create_intervention_type_combo,
        create_dt_cell=create_dt_cell,
        resize_table=resize_table,
    )
    setup_abx_reference_rows(
        abx_table=abx_table,
        create_dt_cell=create_dt_cell,
        create_abx_combo=create_abx_combo,
        resize_table=resize_table,
    )
    setup_ismp_reference_rows(
        ismp_table=ismp_table,
        create_ismp_type_combo=create_ismp_type_combo,
        create_date_cell=create_date_cell,
        resize_table=resize_table,
    )


def setup_diagnosis_reference_rows(
    *,
    diagnosis_table: QTableWidget,
    create_diag_type_combo: CreateComboFn,
    create_icd_combo: CreateComboFn,
    resize_table: ResizeTableFn,
) -> None:
    setup_diagnosis_rows(
        table=diagnosis_table,
        create_type_combo=create_diag_type_combo,
        create_icd_combo=create_icd_combo,
        resize_table=resize_table,
    )


def setup_abx_reference_rows(
    *,
    abx_table: QTableWidget,
    create_dt_cell: CreateDateTimeEditFn,
    create_abx_combo: CreateComboFn,
    resize_table: ResizeTableFn,
) -> None:
    setup_abx_rows(
        table=abx_table,
        create_dt_cell=create_dt_cell,
        create_abx_combo=create_abx_combo,
        resize_table=resize_table,
    )


def setup_ismp_reference_rows(
    *,
    ismp_table: QTableWidget,
    create_ismp_type_combo: CreateComboFn,
    create_date_cell: CreateDateEditFn,
    resize_table: ResizeTableFn,
) -> None:
    setup_ismp_rows(
        table=ismp_table,
        create_type_combo=create_ismp_type_combo,
        create_date_cell=create_date_cell,
        resize_table=resize_table,
    )


def refresh_detail_reference_rows(
    *,
    diagnosis_table: QTableWidget,
    abx_table: QTableWidget,
    ismp_table: QTableWidget,
    create_diag_type_combo: CreateComboFn,
    create_icd_combo: CreateComboFn,
    create_abx_combo: CreateComboFn,
    create_ismp_type_combo: CreateComboFn,
    resize_table: ResizeTableFn,
) -> None:
    refresh_diagnosis_reference_rows(
        table=diagnosis_table,
        create_type_combo=create_diag_type_combo,
        create_icd_combo=create_icd_combo,
    )
    refresh_abx_reference_rows(
        table=abx_table,
        create_abx_combo=create_abx_combo,
    )
    refresh_ismp_reference_rows(
        table=ismp_table,
        create_type_combo=create_ismp_type_combo,
    )
    resize_table(diagnosis_table)
    resize_table(abx_table)
    resize_table(ismp_table)
