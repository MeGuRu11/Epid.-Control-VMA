from __future__ import annotations

import inspect
from datetime import date
from types import SimpleNamespace
from typing import Any, cast

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.dto.auth_dto import SessionContext
from app.ui.analytics.analytics_view import AnalyticsSearchView
from app.ui.main_window import MainWindow
from app.ui.widgets.context_bar import ContextBar


class _ReferenceServiceStub:
    def list_departments(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, name="Тестовое отделение")]

    def list_icd10(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(code="A00", title="Тестовый диагноз")]

    def search_icd10(self, _query: str, limit: int = 50) -> list[SimpleNamespace]:
        _ = limit
        return self.list_icd10()

    def list_microorganisms(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="MIC-1", name="Test microbe")]

    def list_antibiotics(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="ABX-1", name="Test antibiotic")]

    def list_material_types(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="MAT-1", name="Test material")]

    def list_ismp_abbreviations(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(code="ВАП", name="Вентилятор-ассоциированная пневмония", description="Тест")]


class _SavedFilterServiceStub:
    def list_filters(self, _filter_type: str) -> list[SimpleNamespace]:
        return []


class _ReportingServiceStub:
    def list_report_runs(
        self,
        limit: int = 100,
        report_type: str | None = None,
        query: str | None = None,
        verify_hash: bool = False,
    ) -> list[SimpleNamespace]:
        _ = (limit, report_type, query, verify_hash)
        return []


class _AnalyticsServiceStub:
    def clear_cache(self) -> None:
        return None

    def get_aggregates(self, _request: AnalyticsSearchRequest) -> dict[str, Any]:
        return {
            "total": 0,
            "positives": 0,
            "positive_share": 0.0,
            "top_microbes": [],
            "total_microbe_isolations": 0,
        }

    def get_department_summary(
        self,
        _date_from: date | None,
        _date_to: date | None,
        patient_category: str | None = None,
    ) -> list[dict[str, Any]]:
        _ = patient_category
        return []

    def get_trend_by_day(
        self,
        _date_from: date | None,
        _date_to: date | None,
        patient_category: str | None = None,
    ) -> list[dict[str, Any]]:
        _ = patient_category
        return []

    def compare_periods(
        self,
        *,
        current_from: date,
        current_to: date,
        prev_from: date,
        prev_to: date,
        patient_category: str | None = None,
    ) -> dict[str, Any]:
        _ = (current_from, current_to, prev_from, prev_to, patient_category)
        return {
            "current": {"total": 0, "positive_share": 0.0},
            "previous": {"total": 0, "positive_share": 0.0},
        }

    def get_ismp_metrics(
        self,
        _date_from: date | None,
        _date_to: date | None,
        _department_id: int | None,
    ) -> dict[str, Any]:
        return {}


def _session_context() -> SessionContext:
    return SessionContext(user_id=1, login="tester", role="admin")


def test_context_bar_has_compact_contract_without_quick_actions() -> None:
    signature = inspect.signature(ContextBar)

    assert "on_quick_action" not in signature.parameters
    assert not hasattr(MainWindow, "_on_quick_action")


def test_context_bar_uses_change_button_for_compact_panel(qapp, monkeypatch) -> None:
    bar = ContextBar(
        emz_service=cast(Any, SimpleNamespace()),
        patient_service=cast(Any, SimpleNamespace()),
        on_context_change=lambda _patient_id, _case_id: None,
    )
    monkeypatch.setattr(bar, "_animate_content", lambda expanding: bar._on_animation_done(expanding))
    bar.show()
    qapp.processEvents()

    assert bar.change_btn.text() == "Изменить"
    assert not bar.content_widget.isVisible()

    bar._toggle_content()
    qapp.processEvents()
    assert bar.content_widget.isVisible()

    bar._toggle_content()
    qapp.processEvents()
    assert not bar.content_widget.isVisible()

    bar.close()


def test_context_bar_shows_empty_pinned_chips_and_no_navigation_buttons(qapp) -> None:
    bar = ContextBar(
        emz_service=cast(Any, SimpleNamespace()),
        patient_service=cast(Any, SimpleNamespace()),
        on_context_change=lambda _patient_id, _case_id: None,
    )
    bar.show()
    qapp.processEvents()

    assert bar.patient_label.text() == "Пациент не выбран"
    assert bar.case_label.text() == "Госпитализация не выбрана"
    assert not hasattr(bar, "open_emz_btn")
    assert not hasattr(bar, "open_lab_btn")
    assert not hasattr(bar, "open_form100_btn")
    assert not hasattr(bar, "open_san_btn")
    assert not hasattr(bar, "open_analytics_btn")

    bar.close()


def test_context_bar_reset_clears_context_and_search_fields(qapp) -> None:
    calls: list[tuple[int | None, int | None]] = []
    bar = ContextBar(
        emz_service=cast(Any, SimpleNamespace()),
        patient_service=cast(Any, SimpleNamespace()),
        on_context_change=lambda patient_id, case_id: calls.append((patient_id, case_id)),
    )
    bar.show()
    qapp.processEvents()

    bar.patient_search.setText("Иванов")
    bar.case_search.setText("EMZ-123")
    bar._completer_model.setStringList(["1: Иванов Иван"])
    bar._case_model.setStringList(["10: EMZ-123"])
    bar._set_context(1, 10, "Иванов Иван", emit=False)

    bar._reset()

    assert bar.patient_id is None
    assert bar.case_id is None
    assert bar.patient_search.text() == ""
    assert bar.case_search.text() == ""
    assert bar._completer_model.stringList() == []
    assert bar._case_model.stringList() == []
    assert bar.patient_label.text() == "Пациент не выбран"
    assert bar.case_label.text() == "Госпитализация не выбрана"
    assert calls == [(None, None)]

    bar.close()


def test_context_bar_restores_last_patient_without_case(qapp) -> None:
    calls: list[tuple[int | None, int | None]] = []
    bar = ContextBar(
        emz_service=cast(Any, SimpleNamespace()),
        patient_service=cast(Any, SimpleNamespace()),
        on_context_change=lambda patient_id, case_id: calls.append((patient_id, case_id)),
    )
    bar.show()
    qapp.processEvents()

    bar._set_context(7, 12, "Иванов Иван", emit=True)
    bar._clear_patient()
    bar._restore_last_patient()

    assert bar.patient_id == 7
    assert bar.case_id is None
    assert bar.patient_label.text() == "Пациент: 7 Иванов Иван"
    assert bar.case_label.text() == "Госпитализация не выбрана"
    assert calls == [(7, 12), (None, None), (7, None)]

    bar.close()


def test_analytics_saved_filters_toggle_uses_arrow_indicator(qapp) -> None:
    view = AnalyticsSearchView(
        analytics_service=cast(Any, _AnalyticsServiceStub()),
        reference_service=cast(Any, _ReferenceServiceStub()),
        saved_filter_service=cast(Any, _SavedFilterServiceStub()),
        reporting_service=cast(Any, _ReportingServiceStub()),
        session=_session_context(),
    )

    assert view.saved_filters_toggle.text() == "Фильтры ▾"

    view._toggle_saved_filters(True)
    assert view.saved_filters_toggle.text() == "Фильтры ▴"

    view._toggle_saved_filters(False)
    assert view.saved_filters_toggle.text() == "Фильтры ▾"

    view.close()
