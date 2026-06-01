from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from PySide6.QtWidgets import QComboBox

from app.ui.analytics.filter_bar import FilterBar
from app.ui.analytics.tabs.reports_tab import ReportsTab
from app.ui.widgets.table_utils import set_combo_placeholder


class _ReferenceServiceStub:
    def list_departments(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, name="ОРИТ")]

    def list_icd10(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(code="A00", title="Холера")]

    def list_microorganisms(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="ECOLI", name="E. coli")]

    def list_antibiotics(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="AMX", name="Амоксициллин")]

    def list_material_types(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="BLD", name="Кровь")]


class _ReportsControllerStub:
    def load_report_history(self, **_kwargs: object) -> list[Any]:
        return []


def _combo_texts(combo: QComboBox) -> list[str]:
    return [combo.itemText(index) for index in range(combo.count())]


def test_set_combo_placeholder_does_not_add_selectable_item(qapp) -> None:
    combo = QComboBox()
    try:
        combo.addItem("Реальное значение", 1)

        set_combo_placeholder(combo)

        assert combo.placeholderText() == "Выбрать"
        assert combo.currentIndex() == -1
        assert _combo_texts(combo) == ["Реальное значение"]
        assert combo.currentData() is None
    finally:
        combo.close()


def test_analytics_filter_combo_placeholders_are_not_items(qapp) -> None:
    bar = FilterBar(cast(Any, _ReferenceServiceStub()))
    try:
        for combo in (
            bar.department,
            bar.icd10,
            bar.microbe,
            bar.antibiotic,
            bar.material,
            bar.growth_flag,
            bar.patient_category,
        ):
            assert combo.placeholderText() == "Выбрать"
            assert combo.currentIndex() == -1
            assert "Выбрать" not in _combo_texts(combo)
            assert combo.currentData() is None
    finally:
        bar.close()


def test_reports_type_filter_placeholder_is_not_item(qapp) -> None:
    tab = ReportsTab(cast(Any, _ReportsControllerStub()))
    try:
        assert tab.report_type_filter.placeholderText() == "Выбрать"
        assert tab.report_type_filter.currentIndex() == -1
        assert "Выбрать" not in _combo_texts(tab.report_type_filter)
    finally:
        tab.close()
