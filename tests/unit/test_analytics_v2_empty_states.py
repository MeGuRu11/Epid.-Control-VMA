from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

from PySide6.QtWidgets import QLabel

from app.application.dto.analytics_dto import AnalyticsSearchRequest


class _ReferenceServiceStub:
    def list_material_types(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="MAT", name="Material")]


class _EmptyAnalyticsController:
    reference_service = _ReferenceServiceStub()

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

    def get_ismp_metrics(self, _request: AnalyticsSearchRequest) -> dict[str, Any]:
        return {
            "total_cases": 0,
            "ismp_cases": 0,
            "incidence": 0.0,
            "incidence_density": 0.0,
            "prevalence": 0.0,
            "by_type": [],
        }

    def compare_periods(self, _request: AnalyticsSearchRequest, _compare_days: int) -> dict[str, Any] | None:
        return None

    def get_trend(self, _request: AnalyticsSearchRequest) -> list[dict[str, Any]]:
        return []

    def get_department_summary(self, _request: AnalyticsSearchRequest) -> list[dict[str, Any]]:
        return []

    def get_heatmap_data(
        self,
        _request: AnalyticsSearchRequest,
    ) -> tuple[dict[str, dict[str, int]], list[str]]:
        return {}, []

    def get_resistance_data(
        self,
        _request: AnalyticsSearchRequest,
    ) -> dict[str, dict[str, dict[str, int]]]:
        return {}

    def get_ismp_by_department(self, _request: AnalyticsSearchRequest) -> list[tuple[str, int]]:
        return []


def _request() -> AnalyticsSearchRequest:
    return AnalyticsSearchRequest(date_from=date(2026, 1, 1), date_to=date(2026, 1, 31))


def _show_and_refresh(tab: Any, qtbot: Any, qapp: Any) -> None:
    qtbot.addWidget(tab)
    tab.resize(1200, 800)
    tab.show()
    qapp.processEvents()
    tab.refresh(_request())
    qapp.processEvents()


def test_overview_kpi_cards_visible_when_no_data(qtbot: Any, qapp: Any) -> None:
    from app.ui.analytics.tabs.overview_tab import OverviewTab

    tab = OverviewTab(_EmptyAnalyticsController())  # type: ignore[arg-type]
    _show_and_refresh(tab, qtbot, qapp)

    assert tab._kpi_hosp.isVisibleTo(tab)
    assert tab._kpi_ismp.isVisibleTo(tab)
    assert tab._kpi_pos.isVisibleTo(tab)
    assert tab._kpi_prev.isVisibleTo(tab)


def test_overview_trend_shows_placeholder_when_empty(qtbot: Any, qapp: Any) -> None:
    from app.ui.analytics.tabs.overview_tab import OverviewTab

    tab = OverviewTab(_EmptyAnalyticsController())  # type: ignore[arg-type]
    _show_and_refresh(tab, qtbot, qapp)

    assert tab._trend_stack.currentWidget() is tab._trend_empty
    assert tab._trend_empty.objectName() == "inlinePlaceholder"
    assert tab._trend_empty.isVisibleTo(tab)


def test_ismp_kpi_cards_visible_when_no_data(qtbot: Any, qapp: Any) -> None:
    from app.ui.analytics.tabs.ismp_tab import IsmpTab

    tab = IsmpTab(_EmptyAnalyticsController())  # type: ignore[arg-type]
    _show_and_refresh(tab, qtbot, qapp)

    assert tab._kpi_total.isVisibleTo(tab)
    assert tab._kpi_ismp.isVisibleTo(tab)
    assert tab._kpi_inc.isVisibleTo(tab)
    assert tab._kpi_dens.isVisibleTo(tab)
    assert tab._kpi_prev.isVisibleTo(tab)


def test_microbiology_heatmap_shows_placeholder_when_empty(qtbot: Any, qapp: Any) -> None:
    from app.ui.analytics.tabs.microbiology_tab import MicrobiologyTab

    tab = MicrobiologyTab(_EmptyAnalyticsController())  # type: ignore[arg-type]
    _show_and_refresh(tab, qtbot, qapp)

    assert tab._heatmap_stack.currentWidget() is tab._heatmap_empty
    assert tab._heatmap_empty.objectName() == "inlinePlaceholder"
    assert tab._heatmap_empty.isVisibleTo(tab)
    assert tab._chips.isVisibleTo(tab)


def test_inline_placeholders_are_compact_labels(qtbot: Any) -> None:
    from app.ui.analytics.widgets.empty_state import make_inline_placeholder

    label = make_inline_placeholder("No data")
    qtbot.addWidget(label)

    assert isinstance(label, QLabel)
    assert label.objectName() == "inlinePlaceholder"
    assert label.minimumHeight() == 80
