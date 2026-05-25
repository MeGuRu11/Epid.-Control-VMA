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
from app.ui.emz.widgets.row_delete_button import RowDeleteButton


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
        if button.text() == "+ Добавить":
            return button
    raise AssertionError("Кнопка добавления строки вмешательства не найдена")


def _grid_row_for_widget(layout: QGridLayout, widget: QWidget) -> int:
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item is not None and item.widget() is widget:
            row, _, _, _ = cast(tuple[int, int, int, int], layout.getItemPosition(index))
            return row
    raise AssertionError(f"Виджет {widget.objectName() or widget.__class__.__name__} не найден в layout")


def _grid_pos_for_widget(layout: QGridLayout, widget: QWidget) -> tuple[int, int]:
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item is not None and item.widget() is widget:
            row, col, _, _ = cast(tuple[int, int, int, int], layout.getItemPosition(index))
            return row, col
    raise AssertionError(f"Виджет {widget.objectName() or widget.__class__.__name__} не найден в layout")


def test_emz_form_uses_sticky_navigation_and_footer(qapp) -> None:
    form = EmzForm(container=_container(), session=_session())
    try:
        form.show()
        qapp.processEvents()

        assert hasattr(form, "section_nav")
        assert hasattr(form, "save_footer")
        assert hasattr(form, "_scroll_area")
        assert not hasattr(form, "quick_save_btn")
        assert form.save_footer.save_btn.text() == "Сохранить ЭМЗ"
    finally:
        form.close()


def test_patient_layout_uses_four_field_columns(qapp) -> None:
    form = EmzForm(container=_container(), session=_session())
    try:
        layout = cast(QGridLayout, form.form_box.layout())

        assert _grid_pos_for_widget(layout, form.full_name) == (0, 1)
        assert _grid_pos_for_widget(layout, form.dob) == (0, 3)
        assert _grid_pos_for_widget(layout, form.sex) == (0, 5)
        assert _grid_pos_for_widget(layout, form.category_combo) == (0, 7)
        assert _grid_pos_for_widget(layout, form.military_unit) == (1, 1)
        assert _grid_pos_for_widget(layout, form.military_district) == (1, 3)
        assert _grid_pos_for_widget(layout, form.hospital_case_no) == (1, 5)
        assert _grid_pos_for_widget(layout, form.department_combo) == (1, 7)
        assert _grid_pos_for_widget(layout, form.injury_date) == (2, 1)
        assert _grid_pos_for_widget(layout, form.admission_date) == (2, 3)
        assert _grid_pos_for_widget(layout, form.outcome_type_combo) == (2, 5)
        assert _grid_pos_for_widget(layout, form.outcome_date) == (2, 7)
        assert _grid_pos_for_widget(layout, form.severity) == (3, 1)
        assert _grid_pos_for_widget(layout, form.sofa_score) == (3, 3)
        assert _grid_pos_for_widget(layout, form.vph_p_score) == (3, 5)
    finally:
        form.close()


def test_section_counts_follow_required_fields_and_table_rows(qapp) -> None:
    form = EmzForm(container=_container(), session=_session())
    try:
        form.show()
        qapp.processEvents()

        assert form.section_nav._chips["patient"].text() == "Основное (4 незап.)"
        assert not form.save_footer.save_btn.isEnabled()

        form.full_name.setText("Тестовый Пациент")
        form.category_combo.setCurrentIndex(1)
        form.hospital_case_no.setText("CASE-2")
        form.department_combo.setCurrentIndex(1)
        qapp.processEvents()

        assert form.section_nav._chips["patient"].text() == "Основное"
        assert form.save_footer.save_btn.isEnabled()

        form._add_diagnosis_row()
        qapp.processEvents()

        assert form.section_nav._chips["diagnoses"].text() == "Диагнозы (2)"
    finally:
        form.close()


def test_table_sections_are_not_checkable_and_use_inline_add_button(qapp) -> None:
    form = EmzForm(container=_container(), session=_session())
    try:
        for box in (form.diag_box, form.interv_box, form.abx_box, form.ismp_box):
            assert not box.isCheckable()
            buttons = cast(list[QPushButton], box.findChildren(QPushButton))
            add_buttons: list[QPushButton] = [
                button for button in buttons if button.text() == "+ Добавить"
            ]
            assert len(add_buttons) == 1
            assert add_buttons[0].objectName() == "emzInlineAddButton"
            assert not any(button.text() == "Удалить строку" for button in buttons)
    finally:
        form.close()


def test_detail_tables_have_fixed_inline_delete_column(qapp) -> None:
    form = EmzForm(container=_container(), session=_session())
    try:
        table_specs = [
            (form.diagnosis_table, 4, 3, 2),
            (form.intervention_table, 7, 6, 5),
            (form.abx_table, 6, 5, 4),
            (form.ismp_table, 3, 2, 1),
        ]
        for table, column_count, delete_col, stretch_col in table_specs:
            header = table.horizontalHeader()
            assert table.columnCount() == column_count
            assert table.horizontalHeaderItem(delete_col).text() == ""
            assert header.stretchLastSection() is False
            assert header.sectionResizeMode(delete_col).name == "Fixed"
            assert header.sectionResizeMode(stretch_col).name == "Stretch"
            assert table.columnWidth(delete_col) == 30
            assert isinstance(table.cellWidget(0, delete_col), RowDeleteButton)
    finally:
        form.close()


def test_inline_delete_updates_section_count(qapp) -> None:
    form = EmzForm(container=_container(), session=_session())
    try:
        form.show()
        qapp.processEvents()

        form._add_diagnosis_row()
        qapp.processEvents()
        assert form.section_nav._chips["diagnoses"].text() == "Диагнозы (2)"

        button = form.diagnosis_table.cellWidget(1, 3)
        assert isinstance(button, RowDeleteButton)
        button.click()
        qapp.processEvents()

        assert form.diagnosis_table.rowCount() == 1
        assert form.section_nav._chips["diagnoses"].text() == "Диагнозы (1)"
    finally:
        form.close()


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
        admission_row, admission_col = _grid_pos_for_widget(layout, form.admission_date)
        combo_row, combo_col = _grid_pos_for_widget(layout, combo)
        outcome_row, outcome_col = _grid_pos_for_widget(layout, form.outcome_date)
        assert admission_row == combo_row == outcome_row
        assert admission_col < combo_col < outcome_col
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
