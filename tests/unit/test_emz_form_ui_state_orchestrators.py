from __future__ import annotations

from typing import cast

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

from app.ui.emz.form_ui_state_orchestrators import (
    apply_form_read_only_state,
    apply_patient_read_only_state,
    notify_case_selection,
    reset_full_form_fields,
    reset_hospitalization_fields,
    set_quick_action_buttons_visible,
)


class _FakeLineEdit:
    def __init__(self) -> None:
        self.read_only = False
        self.cleared = False

    def setReadOnly(self, value: bool) -> None:  # noqa: N802
        self.read_only = value

    def clear(self) -> None:
        self.cleared = True


class _FakeDateEdit:
    def __init__(self) -> None:
        self.enabled = True
        self.date: object | None = None

    def setEnabled(self, value: bool) -> None:  # noqa: N802
        self.enabled = value

    def setDate(self, value: object) -> None:  # noqa: N802
        self.date = value


class _FakeDateTimeEdit:
    def __init__(self) -> None:
        self.datetime: object | None = None

    def setDateTime(self, value: object) -> None:  # noqa: N802
        self.datetime = value


class _FakeCombo:
    def __init__(self) -> None:
        self.enabled = True
        self.current_index = -1

    def setEnabled(self, value: bool) -> None:  # noqa: N802
        self.enabled = value

    def setCurrentIndex(self, value: int) -> None:  # noqa: N802
        self.current_index = value


class _FakeLabel:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, value: str) -> None:  # noqa: N802
        self.text = value


class _FakeButton:
    def __init__(self) -> None:
        self.enabled = True
        self.visible = True

    def setEnabled(self, value: bool) -> None:  # noqa: N802
        self.enabled = value

    def setVisible(self, value: bool) -> None:  # noqa: N802
        self.visible = value


class _FakeWidget:
    def __init__(self) -> None:
        self.enabled = True

    def setEnabled(self, value: bool) -> None:  # noqa: N802
        self.enabled = value


def test_apply_patient_read_only_state() -> None:
    full_name = _FakeLineEdit()
    dob = _FakeDateEdit()
    sex = _FakeCombo()
    category = _FakeCombo()
    military_unit = _FakeLineEdit()
    military_district = _FakeLineEdit()
    edit_btn = _FakeButton()
    patient_hint = _FakeLabel()

    apply_patient_read_only_state(
        read_only=True,
        edit_mode=False,
        has_current_patient=True,
        full_name=cast(QLineEdit, full_name),
        dob=cast(QDateEdit, dob),
        sex=cast(QComboBox, sex),
        category_combo=cast(QComboBox, category),
        military_unit=cast(QLineEdit, military_unit),
        military_district=cast(QLineEdit, military_district),
        edit_patient_btn=cast(QPushButton, edit_btn),
        patient_hint=cast(QLabel, patient_hint),
        build_patient_hint=lambda read_only, edit_mode: f"{read_only}:{edit_mode}",
    )
    assert full_name.read_only is True
    assert dob.enabled is False
    assert sex.enabled is False
    assert category.enabled is False
    assert military_unit.read_only is True
    assert military_district.read_only is True
    assert edit_btn.enabled is True
    assert edit_btn.visible is True
    assert patient_hint.text == "True:False"


def test_apply_form_read_only_state() -> None:
    section_a = _FakeWidget()
    section_b = _FakeWidget()
    save_btn = _FakeButton()

    apply_form_read_only_state(
        read_only=True,
        sections=(cast(QWidget, section_a), cast(QWidget, section_b)),
        quick_save_btn=cast(QPushButton, save_btn),
    )
    assert section_a.enabled is False
    assert section_b.enabled is False
    assert save_btn.enabled is False


def test_set_quick_action_buttons_visible() -> None:
    new_btn = _FakeButton()
    last_btn = _FakeButton()
    clear_btn = _FakeButton()

    set_quick_action_buttons_visible(
        visible=False,
        quick_new_btn=cast(QPushButton, new_btn),
        quick_last_btn=cast(QPushButton, last_btn),
        quick_clear_btn=cast(QPushButton, clear_btn),
    )
    assert new_btn.visible is False
    assert last_btn.visible is False
    assert clear_btn.visible is False


def test_reset_full_form_fields() -> None:
    full_name = _FakeLineEdit()
    dob = _FakeDateEdit()
    sex = _FakeCombo()
    category = _FakeCombo()
    military_unit = _FakeLineEdit()
    military_district = _FakeLineEdit()
    hospital_case_no = _FakeLineEdit()
    department = _FakeCombo()
    injury = _FakeDateTimeEdit()
    admission = _FakeDateTimeEdit()
    outcome = _FakeDateTimeEdit()
    severity = _FakeLineEdit()
    sofa = _FakeLineEdit()
    vph = _FakeLineEdit()
    resets: list[str] = []
    marker_date = cast(QDate, object())
    marker_dt = cast(QDateTime, object())

    reset_full_form_fields(
        full_name=cast(QLineEdit, full_name),
        dob=cast(QDateEdit, dob),
        sex=cast(QComboBox, sex),
        category_combo=cast(QComboBox, category),
        military_unit=cast(QLineEdit, military_unit),
        military_district=cast(QLineEdit, military_district),
        hospital_case_no=cast(QLineEdit, hospital_case_no),
        department_combo=cast(QComboBox, department),
        injury_date=cast(QDateTimeEdit, injury),
        admission_date=cast(QDateTimeEdit, admission),
        outcome_date=cast(QDateTimeEdit, outcome),
        severity=cast(QLineEdit, severity),
        sofa_score=cast(QLineEdit, sofa),
        vph_p_score=cast(QLineEdit, vph),
        default_date=marker_date,
        default_datetime=marker_dt,
        reset_detail_tables=lambda: resets.append("ok"),
    )
    assert full_name.cleared is True
    assert dob.date is marker_date
    assert sex.current_index == 0
    assert category.current_index == 0
    assert military_unit.cleared is True
    assert military_district.cleared is True
    assert hospital_case_no.cleared is True
    assert department.current_index == 0
    assert injury.datetime is marker_dt
    assert admission.datetime is marker_dt
    assert outcome.datetime is marker_dt
    assert severity.cleared is True
    assert sofa.cleared is True
    assert vph.cleared is True
    assert resets == ["ok"]


def test_reset_hospitalization_fields() -> None:
    hospital_case_no = _FakeLineEdit()
    department = _FakeCombo()
    injury = _FakeDateTimeEdit()
    admission = _FakeDateTimeEdit()
    outcome = _FakeDateTimeEdit()
    severity = _FakeLineEdit()
    sofa = _FakeLineEdit()
    vph = _FakeLineEdit()
    resets: list[str] = []
    marker_dt = cast(QDateTime, object())

    reset_hospitalization_fields(
        hospital_case_no=cast(QLineEdit, hospital_case_no),
        department_combo=cast(QComboBox, department),
        injury_date=cast(QDateTimeEdit, injury),
        admission_date=cast(QDateTimeEdit, admission),
        outcome_date=cast(QDateTimeEdit, outcome),
        severity=cast(QLineEdit, severity),
        sofa_score=cast(QLineEdit, sofa),
        vph_p_score=cast(QLineEdit, vph),
        empty_datetime=marker_dt,
        reset_detail_tables=lambda: resets.append("ok"),
    )
    assert hospital_case_no.cleared is True
    assert department.current_index == 0
    assert injury.datetime is marker_dt
    assert admission.datetime is marker_dt
    assert outcome.datetime is marker_dt
    assert severity.cleared is True
    assert sofa.cleared is True
    assert vph.cleared is True
    assert resets == ["ok"]


def test_notify_case_selection() -> None:
    values: list[tuple[int | None, int | None]] = []
    notify_case_selection(
        callback=lambda patient_id, emr_case_id: values.append((patient_id, emr_case_id)),
        patient_id=5,
        emr_case_id=7,
    )
    notify_case_selection(
        callback=lambda patient_id, emr_case_id: values.append((patient_id, emr_case_id)),
        patient_id=1,
        emr_case_id=2,
        emit=False,
    )
    notify_case_selection(callback=None, patient_id=None, emr_case_id=None)
    assert values == [(5, 7)]
