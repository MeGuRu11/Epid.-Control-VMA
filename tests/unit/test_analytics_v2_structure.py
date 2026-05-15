from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any, cast

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.dto.auth_dto import SessionContext


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

    def search_microorganisms(self, _query: str, limit: int = 50) -> list[SimpleNamespace]:
        _ = limit
        return self.list_microorganisms()

    def list_antibiotics(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="ABX-1", name="Test antibiotic")]

    def search_antibiotics(self, _query: str, limit: int = 50) -> list[SimpleNamespace]:
        _ = limit
        return self.list_antibiotics()

    def list_material_types(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="MAT-1", name="Test material")]

    def search_material_types(self, _query: str, limit: int = 50) -> list[SimpleNamespace]:
        _ = limit
        return self.list_material_types()


class _AnalyticsServiceStub:
    def __init__(self) -> None:
        self.search_request: AnalyticsSearchRequest | None = None
        self.aggregate_request: AnalyticsSearchRequest | None = None
        self.ismp_args: tuple[date | None, date | None, int | None] | None = None

    def clear_cache(self) -> None:
        return None

    def search_samples(self, request: AnalyticsSearchRequest) -> list[object]:
        self.search_request = request
        return []

    def get_aggregates(self, request: AnalyticsSearchRequest) -> dict[str, Any]:
        self.aggregate_request = request
        return {
            "total": 0,
            "positives": 0,
            "positive_share": 0.0,
            "top_microbes": [],
            "total_microbe_isolations": 0,
        }

    def get_ismp_metrics(
        self,
        date_from: date | None,
        date_to: date | None,
        department_id: int | None,
    ) -> dict[str, Any]:
        self.ismp_args = (date_from, date_to, department_id)
        return {}

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


class _SavedFilterServiceStub:
    def list_filters(self, _filter_type: str) -> list[SimpleNamespace]:
        return []

    def save_filter(
        self,
        filter_type: str,
        name: str,
        payload: dict[str, object],
        actor_id: int,
    ) -> SimpleNamespace:
        return SimpleNamespace(filter_type=filter_type, name=name, payload=payload, actor_id=actor_id)

    def delete_filter(self, filter_id: int, actor_id: int) -> bool:
        _ = (filter_id, actor_id)
        return True


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

    def export_analytics_xlsx(
        self,
        request: AnalyticsSearchRequest,
        file_path: str,
        actor_id: int,
    ) -> dict[str, int]:
        _ = (request, file_path, actor_id)
        return {"count": 0}

    def export_analytics_pdf(
        self,
        request: AnalyticsSearchRequest,
        file_path: str,
        actor_id: int,
    ) -> dict[str, int]:
        _ = (request, file_path, actor_id)
        return {"count": 0}


def _session_context() -> SessionContext:
    return SessionContext(user_id=1, login="tester", role="admin")


def _services() -> tuple[_AnalyticsServiceStub, _ReferenceServiceStub, _SavedFilterServiceStub, _ReportingServiceStub]:
    return (
        _AnalyticsServiceStub(),
        _ReferenceServiceStub(),
        _SavedFilterServiceStub(),
        _ReportingServiceStub(),
    )


def _build_view() -> Any:
    from app.ui.analytics.analytics_view_v2 import AnalyticsViewV2

    analytics, reference, saved_filters, reporting = _services()
    return AnalyticsViewV2(
        analytics_service=cast(Any, analytics),
        reference_service=cast(Any, reference),
        saved_filter_service=cast(Any, saved_filters),
        reporting_service=cast(Any, reporting),
        session=_session_context(),
    )


def test_analytics_view_v2_instantiates(qtbot: Any) -> None:
    view = _build_view()
    qtbot.addWidget(view)

    assert view is not None


def test_analytics_view_v2_has_five_tabs(qtbot: Any) -> None:
    view = _build_view()
    qtbot.addWidget(view)

    assert view._tabs.count() == 5
    assert [view._tabs.tabText(index) for index in range(view._tabs.count())] == [
        "Обзор",
        "Микробиология",
        "ИСМП",
        "Поиск",
        "Отчёты",
    ]


def test_analytics_view_v2_filter_bar_present(qtbot: Any) -> None:
    view = _build_view()
    qtbot.addWidget(view)

    assert view._filter_bar is not None


def test_analytics_view_v2_has_set_session_method(qtbot: Any) -> None:
    view = _build_view()
    qtbot.addWidget(view)
    session = SessionContext(user_id=2, login="next", role="operator")

    view.set_session(session)

    assert view.session is session


def test_analytics_view_v2_has_activate_view_method(qtbot: Any) -> None:
    view = _build_view()
    qtbot.addWidget(view)

    view.activate_view()

    assert view._default_analytics_loaded is True


def test_analytics_controller_search_delegates_to_service() -> None:
    from app.ui.analytics.controller import AnalyticsController

    analytics, reference, saved_filters, reporting = _services()
    controller = AnalyticsController(
        analytics_service=cast(Any, analytics),
        reference_service=cast(Any, reference),
        saved_filter_service=cast(Any, saved_filters),
        reporting_service=cast(Any, reporting),
    )
    request = AnalyticsSearchRequest(date_from=date(2026, 1, 1), date_to=date(2026, 1, 31))

    assert controller.search(request) == []
    assert analytics.search_request is request


def test_analytics_controller_get_aggregates_delegates() -> None:
    from app.ui.analytics.controller import AnalyticsController

    analytics, reference, saved_filters, reporting = _services()
    controller = AnalyticsController(
        analytics_service=cast(Any, analytics),
        reference_service=cast(Any, reference),
        saved_filter_service=cast(Any, saved_filters),
        reporting_service=cast(Any, reporting),
    )
    request = AnalyticsSearchRequest(date_from=date(2026, 2, 1), date_to=date(2026, 2, 28))

    assert controller.get_aggregates(request)["total"] == 0
    assert analytics.aggregate_request is request


def test_analytics_controller_get_ismp_metrics_delegates() -> None:
    from app.ui.analytics.controller import AnalyticsController

    analytics, reference, saved_filters, reporting = _services()
    controller = AnalyticsController(
        analytics_service=cast(Any, analytics),
        reference_service=cast(Any, reference),
        saved_filter_service=cast(Any, saved_filters),
        reporting_service=cast(Any, reporting),
    )
    request = AnalyticsSearchRequest(
        date_from=date(2026, 3, 1),
        date_to=date(2026, 3, 31),
        department_id=5,
    )

    controller.get_ismp_metrics(request)

    assert analytics.ismp_args == (date(2026, 3, 1), date(2026, 3, 31), 5)


def test_filter_bar_emits_filters_changed_on_period_change(qtbot: Any) -> None:
    from app.ui.analytics.filter_bar import FilterBar

    bar = FilterBar(reference_service=cast(Any, _ReferenceServiceStub()))
    qtbot.addWidget(bar)
    seven_days_index = bar.quick_period.findData("7d")
    assert seven_days_index >= 0

    emitted: list[AnalyticsSearchRequest] = []
    bar.filters_changed.connect(emitted.append)
    bar.quick_period.setCurrentIndex(seven_days_index)
    qtbot.waitUntil(lambda: len(emitted) == 1, timeout=1000)

    assert isinstance(emitted[0], AnalyticsSearchRequest)


def test_overview_tab_has_four_kpi_cards(qtbot: Any) -> None:
    from app.ui.analytics.widgets.kpi_card import KpiCard

    view = _build_view()
    qtbot.addWidget(view)

    assert len(view._overview_tab.findChildren(KpiCard)) == 4


def test_overview_tab_has_drill_down_signal(qtbot: Any) -> None:
    from app.ui.analytics.tabs import TAB_ISMP

    view = _build_view()
    qtbot.addWidget(view)
    emitted: list[int] = []
    view._overview_tab.drill_down_requested.connect(emitted.append)

    view._overview_tab.drill_down_requested.emit(TAB_ISMP)

    assert emitted == [TAB_ISMP]


def test_drill_down_signal_connected_to_tabs(qtbot: Any) -> None:
    from PySide6.QtCore import Qt

    from app.ui.analytics.tabs import TAB_MICROBIOLOGY, TAB_OVERVIEW

    view = _build_view()
    qtbot.addWidget(view)
    assert view._tabs.currentIndex() == TAB_OVERVIEW
    view._filter_bar.patient_name.setText("Иванов")
    qtbot.waitUntil(lambda: view._current_request is not None, timeout=1000)

    qtbot.mouseClick(view._overview_tab._kpi_pos, Qt.MouseButton.LeftButton)

    assert view._tabs.currentIndex() == TAB_MICROBIOLOGY
    assert view._current_request is not None
    assert view._current_request.patient_name == "Иванов"
