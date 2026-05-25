from __future__ import annotations

from collections.abc import Callable
from datetime import date
from types import SimpleNamespace
from typing import Any, cast

from PySide6.QtWidgets import QDialogButtonBox, QPushButton

from app.application.dto.emz_dto import EmzCaseDetail
from app.container import Container
from app.domain.constants import MilitaryCategory
from app.ui.emz.emz_edit_dialog import EmzEditDialog


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


def _container() -> Container:
    return cast(
        Container,
        SimpleNamespace(reference_service=_ReferenceServiceStub(), emz_service=_EmzServiceStub()),
    )


def _footer_close_button(dialog: EmzEditDialog) -> QPushButton:
    buttons = cast(list[QPushButton], dialog.form.save_footer.findChildren(QPushButton))
    for button in buttons:
        if button.text() == "Закрыть":
            return button
    raise AssertionError("Кнопка закрытия в footer не найдена")


def test_edit_dialog_uses_single_footer_button_row(qtbot: Any) -> None:
    dialog = EmzEditDialog(container=_container(), patient_id=7, emr_case_id=42)
    qtbot.addWidget(dialog)
    try:
        assert dialog.findChildren(QDialogButtonBox) == []
        assert dialog.form.save_footer.save_btn.text() == "Сохранить изменения"
        assert _footer_close_button(dialog).text() == "Закрыть"
    finally:
        dialog.close()


def test_edit_dialog_footer_close_button_rejects(qtbot: Any) -> None:
    dialog = EmzEditDialog(container=_container(), patient_id=7, emr_case_id=42)
    qtbot.addWidget(dialog)
    try:
        rejected: list[bool] = []
        dialog.rejected.connect(cast(Callable[[], None], lambda: rejected.append(True)))

        _footer_close_button(dialog).click()

        assert rejected == [True]
    finally:
        dialog.close()
