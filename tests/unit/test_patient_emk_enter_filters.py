from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

from PySide6.QtCore import QDate, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton

from app.application.dto.auth_dto import SessionContext
from app.application.dto.emz_dto import EmzCaseDetail, EmzCaseResponse
from app.application.dto.patient_dto import PatientResponse
from app.ui.patient.patient_emk_view import PatientEmkView


class _PatientServiceStub:
    pass


class _EmzServiceStub:
    pass


class _ReferenceServiceStub:
    def list_departments(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, name="ОРИТ")]


def _make_detail(case_id: int, admitted_at: datetime) -> EmzCaseDetail:
    return EmzCaseDetail(
        id=case_id,
        patient_id=7,
        patient_full_name="Иванов Иван",
        patient_dob=None,
        patient_sex="M",
        patient_category=None,
        patient_military_unit=None,
        patient_military_district=None,
        hospital_case_no=f"CASE-{case_id}",
        department_id=1,
        version_no=1,
        admission_date=admitted_at,
        injury_date=None,
        outcome_date=None,
        outcome_type=None,
        severity=None,
        sofa_score=None,
        vph_p_or_score=None,
        diagnoses=[],
        interventions=[],
        antibiotic_courses=[],
        ismp_cases=[],
    )


def _make_response(case_id: int) -> EmzCaseResponse:
    return EmzCaseResponse(
        id=case_id,
        version_id=case_id,
        version_no=1,
        is_current=True,
        valid_from=datetime(2026, 5, 1, tzinfo=UTC),
        valid_to=None,
        days_to_admission=None,
        length_of_stay_days=None,
    )


def _make_view(qapp) -> PatientEmkView:
    view = PatientEmkView(
        patient_service=cast(Any, _PatientServiceStub()),
        emz_service=cast(Any, _EmzServiceStub()),
        reference_service=cast(Any, _ReferenceServiceStub()),
        session=SessionContext(user_id=1, login="tester", role="admin"),
        on_open_emz=lambda _patient_id, _case_id: None,
        on_open_lab=lambda _patient_id, _case_id: None,
    )
    view._current_patient = PatientResponse(id=7, full_name="Иванов Иван", dob=None, sex="M")
    view._cases_cache = [
        (_make_detail(1, datetime(2026, 5, 20, 8, 0, tzinfo=UTC)), _make_response(1)),
        (_make_detail(2, datetime(2026, 5, 22, 8, 0, tzinfo=UTC)), _make_response(2)),
    ]
    view._apply_case_filters()
    view.show()
    qapp.processEvents()
    return view


def test_patient_emk_case_date_filters_apply_on_enter_only(qapp) -> None:
    view = _make_view(qapp)
    try:
        assert view.cases_table.rowCount() == 2

        view.date_from.setDate(QDate(2026, 5, 21))
        qapp.processEvents()

        assert view.cases_table.rowCount() == 2

        view.date_from.setFocus()
        qapp.processEvents()
        QTest.keyClick(view.date_from, Qt.Key.Key_Return)
        qapp.processEvents()

        assert view.cases_table.rowCount() == 1
        case_id_item = view.cases_table.item(0, 5)
        assert case_id_item is not None
        assert case_id_item.text() == "2"

        view._reset_filters()
        qapp.processEvents()
        assert view.cases_table.rowCount() == 2

        view.date_to.setDate(QDate(2026, 5, 21))
        qapp.processEvents()

        assert view.cases_table.rowCount() == 2

        view.date_to.setFocus()
        qapp.processEvents()
        QTest.keyClick(view.date_to, Qt.Key.Key_Return)
        qapp.processEvents()

        assert view.cases_table.rowCount() == 1
        case_id_item = view.cases_table.item(0, 5)
        assert case_id_item is not None
        assert case_id_item.text() == "1"
    finally:
        view.close()


def test_patient_emk_no_button_is_default(qapp) -> None:
    view = _make_view(qapp)
    try:
        buttons = cast(list[QPushButton], view.findChildren(QPushButton))
        assert buttons
        for button in buttons:
            assert not button.isDefault()
            assert not button.autoDefault()
    finally:
        view.close()
