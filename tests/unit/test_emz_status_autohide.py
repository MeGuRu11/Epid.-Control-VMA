"""Status label auto-hides for info/success and persists for errors."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any, cast

from app.application.dto.auth_dto import SessionContext
from app.application.dto.emz_dto import EmzCaseDetail
from app.container import Container
from app.domain.constants import MilitaryCategory
from app.ui.emz.emz_form import EmzForm


class _ReferenceServiceStub:
    def list_departments(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, name="Тестовое отделение")]

    def list_icd10(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(code="A00", title="Тестовый диагноз")]

    def list_antibiotics(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="ABX-1", name="Test antibiotic")]

    def list_ismp_abbreviations(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(code="ВАП", name="ВАП", description="Тест")]


class _EmzServiceStub:
    def get_current(self, _emr_case_id: int) -> EmzCaseDetail:
        return EmzCaseDetail(
            id=42,
            patient_id=7,
            patient_full_name="Тестовый Пациент",
            patient_dob=date(1990, 1, 1),
            patient_sex="M",
            patient_category=MilitaryCategory.OFFICER.value,
            patient_military_unit=None,
            patient_military_district=None,
            hospital_case_no="CASE-1",
            department_id=1,
            version_no=1,
            admission_date=None,
            injury_date=None,
            outcome_date=None,
            severity=None,
            sofa_score=None,
            vph_p_or_score=None,
            diagnoses=[],
            interventions=[],
            antibiotic_courses=[],
            ismp_cases=[],
        )


def _session() -> SessionContext:
    return SessionContext(user_id=1, login="tester", role="admin")


def _container() -> Container:
    return cast(
        Container,
        SimpleNamespace(reference_service=_ReferenceServiceStub(), emz_service=_EmzServiceStub()),
    )


def test_status_info_auto_hides(qtbot: Any) -> None:
    form = EmzForm(container=_container(), session=_session())
    qtbot.addWidget(form)

    form._set_status_with_timeout("Тестовое сообщение", "info")

    assert form.status_label.text() == "Тестовое сообщение"
    assert form._status_hide_timer.isActive()

    qtbot.wait(4100)

    assert form.status_label.text() == ""


def test_status_success_auto_hides(qtbot: Any) -> None:
    form = EmzForm(container=_container(), session=_session())
    qtbot.addWidget(form)

    form._set_status_with_timeout("ЭМЗ открыта.", "success")

    assert form.status_label.text() == "ЭМЗ открыта."
    assert form._status_hide_timer.isActive()

    qtbot.wait(4100)

    assert form.status_label.text() == ""


def test_status_error_persists(qtbot: Any) -> None:
    form = EmzForm(container=_container(), session=_session())
    qtbot.addWidget(form)

    form._set_status_with_timeout("Ошибка!", "error")

    assert form.status_label.text() == "Ошибка!"
    assert not form._status_hide_timer.isActive()
