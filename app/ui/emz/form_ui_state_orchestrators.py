from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import QDate, QDateTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

PatientHintBuilder = Callable[[bool, bool], str]
CaseSelectionCallback = Callable[[int | None, int | None], None]


def apply_patient_read_only_state(
    *,
    read_only: bool,
    edit_mode: bool,
    has_current_patient: bool,
    full_name: QLineEdit,
    dob: QDateEdit,
    sex: QComboBox,
    category_combo: QComboBox,
    military_unit: QLineEdit,
    military_district: QLineEdit,
    edit_patient_btn: QPushButton,
    patient_hint: QLabel,
    build_patient_hint: PatientHintBuilder,
) -> None:
    full_name.setReadOnly(read_only)
    dob.setEnabled(not read_only)
    sex.setEnabled(not read_only)
    category_combo.setEnabled(not read_only)
    military_unit.setReadOnly(read_only)
    military_district.setReadOnly(read_only)
    can_edit_patient = has_current_patient and read_only and not edit_mode
    edit_patient_btn.setEnabled(can_edit_patient)
    edit_patient_btn.setVisible(can_edit_patient)
    patient_hint.setText(build_patient_hint(read_only, edit_mode))


def apply_form_read_only_state(
    *,
    read_only: bool,
    sections: Sequence[QWidget],
    quick_save_btn: QPushButton,
) -> None:
    for section in sections:
        section.setEnabled(not read_only)
    quick_save_btn.setEnabled(not read_only)


def set_quick_action_buttons_visible(
    *,
    visible: bool,
    quick_new_btn: QPushButton,
    quick_last_btn: QPushButton,
    quick_clear_btn: QPushButton,
) -> None:
    quick_new_btn.setVisible(visible)
    quick_last_btn.setVisible(visible)
    quick_clear_btn.setVisible(visible)


def reset_full_form_fields(
    *,
    full_name: QLineEdit,
    dob: QDateEdit,
    sex: QComboBox,
    category_combo: QComboBox,
    military_unit: QLineEdit,
    military_district: QLineEdit,
    hospital_case_no: QLineEdit,
    department_combo: QComboBox,
    injury_date: QDateTimeEdit,
    admission_date: QDateTimeEdit,
    outcome_date: QDateTimeEdit,
    severity: QLineEdit,
    sofa_score: QLineEdit,
    vph_p_score: QLineEdit,
    default_date: QDate,
    default_datetime: QDateTime,
    reset_detail_tables: Callable[[], None],
) -> None:
    full_name.clear()
    dob.setDate(default_date)
    sex.setCurrentIndex(0)
    category_combo.setCurrentIndex(0)
    military_unit.clear()
    military_district.clear()
    hospital_case_no.clear()
    department_combo.setCurrentIndex(0)
    injury_date.setDateTime(default_datetime)
    admission_date.setDateTime(default_datetime)
    outcome_date.setDateTime(default_datetime)
    severity.clear()
    sofa_score.clear()
    vph_p_score.clear()
    reset_detail_tables()


def reset_hospitalization_fields(
    *,
    hospital_case_no: QLineEdit,
    department_combo: QComboBox,
    injury_date: QDateTimeEdit,
    admission_date: QDateTimeEdit,
    outcome_date: QDateTimeEdit,
    severity: QLineEdit,
    sofa_score: QLineEdit,
    vph_p_score: QLineEdit,
    empty_datetime: QDateTime,
    reset_detail_tables: Callable[[], None],
) -> None:
    hospital_case_no.clear()
    department_combo.setCurrentIndex(0)
    injury_date.setDateTime(empty_datetime)
    admission_date.setDateTime(empty_datetime)
    outcome_date.setDateTime(empty_datetime)
    severity.clear()
    sofa_score.clear()
    vph_p_score.clear()
    reset_detail_tables()


def notify_case_selection(
    *,
    callback: CaseSelectionCallback | None,
    patient_id: int | None,
    emr_case_id: int | None,
    emit: bool = True,
) -> None:
    if emit and callback:
        callback(patient_id, emr_case_id)
