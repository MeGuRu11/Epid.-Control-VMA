from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import cast

from PySide6.QtCore import QDate, QDateTime, Qt, QTime
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QComboBox, QDateTimeEdit, QGridLayout, QPushButton, QWidget

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
        return [SimpleNamespace(code="ВАП", name="Вентилятор-ассоциированная пневмония", description="Тест")]


class _EmzServiceStub:
    def __init__(self, detail: EmzCaseDetail) -> None:
        self.detail = detail

    def get_current(self, _emr_case_id: int) -> EmzCaseDetail:
        return self.detail


def _session() -> SessionContext:
    return SessionContext(user_id=1, login="tester", role="admin")


def _empty_interventions_detail() -> EmzCaseDetail:
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
        admission_date=datetime(2026, 1, 10, 8, 0, tzinfo=UTC),
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


def _container(detail: EmzCaseDetail | None = None) -> Container:
    return cast(
        Container,
        SimpleNamespace(
            reference_service=_ReferenceServiceStub(),
            emz_service=_EmzServiceStub(detail or _empty_interventions_detail()),
        ),
    )


def _assert_intervention_row_widgets(form: EmzForm, row: int) -> None:
    assert isinstance(form.intervention_table.cellWidget(row, 0), QComboBox)
    start = form.intervention_table.cellWidget(row, 1)
    end = form.intervention_table.cellWidget(row, 2)
    assert isinstance(start, QDateTimeEdit)
    assert isinstance(end, QDateTimeEdit)
    assert start.displayFormat() == "dd.MM.yyyy HH:mm"
    assert end.displayFormat() == "dd.MM.yyyy HH:mm"
    assert start.dateTime() == form._dt_empty
    assert end.dateTime() == form._dt_empty


def _intervention_add_button(form: EmzForm) -> QPushButton:
    for button in cast(list[QPushButton], form.interv_box.findChildren(QPushButton)):
        if button.text() == "Добавить строку":
            return button
    raise AssertionError("Кнопка добавления строки вмешательства не найдена")


def _grid_row_for_widget(layout: QGridLayout, widget: QWidget) -> int:
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item is not None and item.widget() is widget:
            row, _, _, _ = cast(tuple[int, int, int, int], layout.getItemPosition(index))
            return row
    raise AssertionError(f"Виджет {widget.objectName() or widget.__class__.__name__} не найден в layout")


def test_edit_form_initializes_intervention_row_for_empty_items(qapp) -> None:
    form = EmzForm(container=_container(), session=_session())
    try:
        form.set_edit_mode(True)
        form.show()
        qapp.processEvents()

        form.load_case(7, 42, emit_context=False)
        qapp.processEvents()

        assert form.intervention_table.rowCount() >= 1
        _assert_intervention_row_widgets(form, 0)
    finally:
        form.close()


def test_form_contains_outcome_type_combo_between_admission_and_outcome(qapp) -> None:
    form = EmzForm(container=_container(), session=_session())
    try:
        form.show()
        qapp.processEvents()

        combo = form.outcome_type_combo
        assert isinstance(combo, QComboBox)
        assert form.outcome_type_label.text() == "Исход"
        assert combo.itemText(0) == "Не выбран"
        assert combo.itemData(0) is None
        assert [combo.itemText(index) for index in range(1, combo.count())] == [
            "Выписка",
            "Перевод",
            "Летальный исход",
        ]
        assert [combo.itemData(index) for index in range(1, combo.count())] == [
            "discharge",
            "transfer",
            "death",
        ]

        layout = cast(QGridLayout, form.form_box.layout())
        assert _grid_row_for_widget(layout, form.admission_date) < _grid_row_for_widget(layout, combo)
        assert _grid_row_for_widget(layout, combo) < _grid_row_for_widget(layout, form.outcome_date)
    finally:
        form.close()


def test_form_applies_outcome_type_from_detail(qapp) -> None:
    detail = _empty_interventions_detail().model_copy(update={"outcome_type": "transfer"})
    form = EmzForm(container=_container(detail), session=_session())
    try:
        form.set_edit_mode(True)
        form.show()
        qapp.processEvents()

        form.load_case(7, 42, emit_context=False)
        qapp.processEvents()

        assert form.outcome_type_combo.currentText() == "Перевод"
        assert form.outcome_type_combo.currentData() == "transfer"
    finally:
        form.close()


def test_form_collects_selected_outcome_type_in_payload(qapp) -> None:
    form = EmzForm(container=_container(), session=_session())
    try:
        index = form.outcome_type_combo.findData("death")
        assert index >= 0
        form.outcome_type_combo.setCurrentIndex(index)

        payload = form._build_payload()

        assert payload.outcome_type == "death"
    finally:
        form.close()


def test_form_keeps_old_case_without_outcome_type_on_placeholder(qapp) -> None:
    form = EmzForm(container=_container(_empty_interventions_detail()), session=_session())
    try:
        form.set_edit_mode(True)
        form.show()
        qapp.processEvents()

        form.load_case(7, 42, emit_context=False)
        qapp.processEvents()

        assert form.outcome_type_combo.currentIndex() == 0
        assert form.outcome_type_combo.currentData() is None
        assert form._outcome_type_value() is None
    finally:
        form.close()


def test_intervention_add_button_creates_initialized_row(qapp) -> None:
    form = EmzForm(container=_container(), session=_session())
    try:
        form.show()
        qapp.processEvents()
        initial_rows = form.intervention_table.rowCount()

        QTest.mouseClick(_intervention_add_button(form), Qt.MouseButton.LeftButton)
        qapp.processEvents()

        assert form.intervention_table.rowCount() == initial_rows + 1
        _assert_intervention_row_widgets(form, initial_rows)
    finally:
        form.close()


def test_emz_form_reset_keeps_datetime_fields_empty_not_current(qapp) -> None:
    form = EmzForm(container=_container(), session=_session())
    try:
        explicit = QDateTime(QDate(2026, 1, 10), QTime(8, 30))
        form.injury_date.setDateTime(explicit)
        form.admission_date.setDateTime(explicit)
        form.outcome_date.setDateTime(explicit)

        form._reset_form(emit_context=False)
        qapp.processEvents()

        assert form._date_value(form.dob) is None
        assert form.injury_date.dateTime() == form._dt_empty
        assert form.admission_date.dateTime() == form._dt_empty
        assert form.outcome_date.dateTime() == form._dt_empty
        assert form._datetime_value(form.admission_date) is None
    finally:
        form.close()


def test_intervention_datetime_cell_collects_explicit_time(qapp) -> None:
    form = EmzForm(container=_container(), session=_session())
    try:
        widget = form.intervention_table.cellWidget(0, 1)
        assert isinstance(widget, QDateTimeEdit)

        widget.setDateTime(QDateTime(QDate(2024, 1, 1), QTime(8, 30)))
        value = form._dt_from_cell(widget)

        assert value is not None
        assert value.hour == 8
        assert value.minute == 30
    finally:
        form.close()
