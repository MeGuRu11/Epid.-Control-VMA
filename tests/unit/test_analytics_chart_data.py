from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QAbstractItemView

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.dto.auth_dto import SessionContext
from app.ui.analytics.analytics_view_v2 import AnalyticsViewV2
from app.ui.analytics.chart_data import (
    AUTO_DAY_MAX_DAYS,
    AUTO_WEEK_MAX_DAYS,
    TimeGrouping,
    TimeSeriesPoint,
    group_time_series,
    group_trend_rows,
    resolve_time_grouping,
)


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

    def search_samples(self, _request: AnalyticsSearchRequest) -> list[object]:
        return []

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

    def get_ismp_by_department(
        self,
        _date_from: date | None,
        _date_to: date | None,
    ) -> list[tuple[str, int]]:
        return []


class _ChartCapture:
    def __init__(self) -> None:
        self.items: list[tuple[str, float]] = []

    def update_data(self, items: list[tuple[str, float]] | tuple[tuple[str, float], ...] | Any) -> None:
        self.items = list(items)


def _session_context() -> SessionContext:
    return SessionContext(user_id=1, login="tester", role="admin")


def _build_view() -> AnalyticsViewV2:
    return AnalyticsViewV2(
        analytics_service=cast(Any, _AnalyticsServiceStub()),
        reference_service=cast(Any, _ReferenceServiceStub()),
        saved_filter_service=cast(Any, _SavedFilterServiceStub()),
        reporting_service=cast(Any, _ReportingServiceStub()),
        session=_session_context(),
    )


def _combo_labels(combo: Any) -> list[str]:
    return [combo.itemText(index) for index in range(combo.count())]


def _combo_values(combo: Any) -> list[object]:
    return [combo.itemData(index) for index in range(combo.count())]


@pytest.mark.parametrize(
    ("period_days", "expected"),
    [
        (7, TimeGrouping.DAY),
        (AUTO_DAY_MAX_DAYS, TimeGrouping.DAY),
        (AUTO_DAY_MAX_DAYS + 1, TimeGrouping.WEEK),
        (AUTO_WEEK_MAX_DAYS, TimeGrouping.WEEK),
        (AUTO_WEEK_MAX_DAYS + 1, TimeGrouping.MONTH),
    ],
)
def test_resolve_time_grouping_auto_thresholds(period_days: int, expected: TimeGrouping) -> None:
    start_date = date(2026, 1, 1)
    end_date = start_date + timedelta(days=period_days - 1)

    assert resolve_time_grouping(TimeGrouping.AUTO, start_date, end_date) is expected


@pytest.mark.parametrize("requested", [TimeGrouping.DAY, TimeGrouping.WEEK, TimeGrouping.MONTH])
def test_resolve_time_grouping_keeps_explicit_value(requested: TimeGrouping) -> None:
    assert resolve_time_grouping(requested, date(2026, 1, 1), date(2026, 12, 31)) is requested


def test_group_time_series_day_sorts_points_and_sums_duplicate_dates() -> None:
    points = [
        TimeSeriesPoint(date(2026, 4, 3), 4),
        TimeSeriesPoint(date(2026, 4, 1), 1),
        TimeSeriesPoint(date(2026, 4, 1), 2),
    ]

    result = group_time_series(points, TimeGrouping.DAY, date(2026, 4, 1), date(2026, 4, 3))

    assert result.effective_grouping is TimeGrouping.DAY
    assert result.labels == ["01.04.2026", "03.04.2026"]
    assert result.values == [3, 4]


def test_group_time_series_week_sums_iso_week_values() -> None:
    points = [
        TimeSeriesPoint(date(2026, 4, 20), 2),
        TimeSeriesPoint(date(2026, 4, 22), 3),
    ]

    result = group_time_series(points, TimeGrouping.WEEK, date(2026, 4, 20), date(2026, 4, 26))

    assert result.labels == ["2026-W17"]
    assert result.values == [5]


def test_group_time_series_week_splits_different_weeks() -> None:
    points = [
        TimeSeriesPoint(date(2026, 4, 20), 2),
        TimeSeriesPoint(date(2026, 4, 27), 3),
    ]

    result = group_time_series(points, TimeGrouping.WEEK, date(2026, 4, 20), date(2026, 5, 3))

    assert result.labels == ["2026-W17", "2026-W18"]
    assert result.values == [2, 3]


def test_group_time_series_week_handles_year_boundary() -> None:
    points = [
        TimeSeriesPoint(date(2025, 12, 29), 2),
        TimeSeriesPoint(date(2026, 1, 4), 3),
        TimeSeriesPoint(date(2026, 1, 5), 4),
    ]

    result = group_time_series(points, TimeGrouping.WEEK, date(2025, 12, 29), date(2026, 1, 5))

    assert result.labels == ["2026-W01", "2026-W02"]
    assert result.values == [5, 4]


def test_group_time_series_month_sums_and_splits_calendar_months() -> None:
    points = [
        TimeSeriesPoint(date(2026, 4, 30), 2),
        TimeSeriesPoint(date(2026, 4, 1), 3),
        TimeSeriesPoint(date(2026, 5, 1), 4),
    ]

    result = group_time_series(points, TimeGrouping.MONTH, date(2026, 4, 1), date(2026, 5, 31))

    assert result.labels == ["04.2026", "05.2026"]
    assert result.values == [5, 4]


def test_group_time_series_auto_returns_effective_grouping() -> None:
    start_date = date(2026, 1, 1)
    end_date = start_date + timedelta(days=89)

    result = group_time_series(
        [TimeSeriesPoint(start_date, 1), TimeSeriesPoint(end_date, 2)],
        TimeGrouping.AUTO,
        start_date,
        end_date,
    )

    assert result.effective_grouping is TimeGrouping.WEEK
    assert result.labels[0] == "2026-W01"


def test_group_time_series_empty_list_does_not_fail() -> None:
    result = group_time_series([], TimeGrouping.AUTO, date(2026, 1, 1), date(2026, 1, 7))

    assert result.labels == []
    assert result.values == []
    assert result.effective_grouping is TimeGrouping.DAY


def test_group_trend_rows_week_aggregates_totals_before_percentage() -> None:
    result = group_trend_rows(
        [
            {"day": "2026-04-20", "total": 1, "positives": 1},
            {"day": "2026-04-21", "total": 99, "positives": 0},
        ],
        requested=TimeGrouping.WEEK,
        date_from=date(2026, 4, 20),
        date_to=date(2026, 4, 26),
    )

    assert result.labels == ["2026-W17"]
    assert result.values == [1.0]


def test_group_trend_rows_day_preserves_zero_filled_period() -> None:
    result = group_trend_rows(
        [{"day": "2026-04-01", "total": 10, "positives": 5}],
        requested=TimeGrouping.DAY,
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 3),
    )

    assert result.labels == ["01.04.2026", "02.04.2026", "03.04.2026"]
    assert result.values == [50.0, 0.0, 0.0]


def test_group_trend_rows_week_on_ninety_days_has_fewer_points_than_day() -> None:
    start_date = date(2026, 1, 1)
    end_date = start_date + timedelta(days=89)
    rows = [
        {"day": (start_date + timedelta(days=offset)).isoformat(), "total": 1, "positives": 1}
        for offset in range(90)
    ]

    daily = group_trend_rows(rows, requested=TimeGrouping.DAY, date_from=start_date, date_to=end_date)
    weekly = group_trend_rows(rows, requested=TimeGrouping.WEEK, date_from=start_date, date_to=end_date)

    assert len(daily.values) == 90
    assert len(weekly.values) < len(daily.values)


def test_apply_search_results_sends_percentage_share_to_top_microbes_chart(qapp) -> None:
    view = _build_view()
    overview = view._overview_tab
    overview.chart = cast(Any, _ChartCapture())

    overview._apply_aggregate_summary(
        {
            "total": 8,
            "positives": 4,
            "positive_share": 0.5,
            "top_microbes": [("ECO - E. coli", 3), ("SAU - S. aureus", 1)],
            "total_microbe_isolations": 4,
        }
    )

    assert overview.summary_share.text() == "Доля: 50.0%"
    assert cast(_ChartCapture, overview.chart).items == [
        ("ECO - E. coli", 75.0),
        ("SAU - S. aureus", 25.0),
    ]
    assert overview.top_table.columnCount() == 3
    first_name_item = overview.top_table.item(0, 0)
    first_count_item = overview.top_table.item(0, 1)
    first_share_item = overview.top_table.item(0, 2)
    second_share_item = overview.top_table.item(1, 2)
    assert first_name_item is not None
    assert first_count_item is not None
    assert first_share_item is not None
    assert second_share_item is not None
    assert first_name_item.text() == "ECO - E. coli"
    assert first_count_item.text() == "3"
    assert first_share_item.text() == "75.0%"
    assert second_share_item.text() == "25.0%"
    view.close()


def test_apply_trend_sends_real_dates_and_daily_percentage_to_chart(qapp) -> None:
    view = _build_view()
    overview = view._overview_tab
    overview.trend_chart = cast(Any, _ChartCapture())

    overview._apply_trend(
        rows=[
            {"day": "2026-04-01", "total": 10, "positives": 5},
            {"day": "2026-04-03", "total": 4, "positives": 1},
        ],
        request=AnalyticsSearchRequest(date_from=date(2026, 4, 1), date_to=date(2026, 4, 3)),
    )

    assert cast(_ChartCapture, overview.trend_chart).items == [
        ("01.04.2026", 50.0),
        ("02.04.2026", 0.0),
        ("03.04.2026", 25.0),
    ]
    view.close()


def test_analytics_time_grouping_combo_is_visible_in_dashboard_controls(qapp) -> None:
    view = _build_view()
    overview = view._overview_tab
    view.show()
    qapp.processEvents()

    assert overview.time_grouping.count() == 4
    assert overview.time_grouping.currentData() == TimeGrouping.AUTO.value
    assert _combo_labels(overview.time_grouping) == ["Авто", "Дни", "Недели", "Месяцы"]
    assert _combo_values(overview.time_grouping) == [
        TimeGrouping.AUTO.value,
        TimeGrouping.DAY.value,
        TimeGrouping.WEEK.value,
        TimeGrouping.MONTH.value,
    ]
    view.close()


def test_analytics_compare_period_and_time_grouping_are_separate_controls(qapp) -> None:
    view = _build_view()
    overview = view._overview_tab

    assert overview.compare_period is not overview.time_grouping
    assert _combo_labels(overview.compare_period) == ["Неделя", "Месяц"]
    assert _combo_values(overview.compare_period) == [7, 30]
    assert _combo_labels(overview.time_grouping) == ["Авто", "Дни", "Недели", "Месяцы"]
    assert _combo_values(overview.time_grouping) == [
        TimeGrouping.AUTO.value,
        TimeGrouping.DAY.value,
        TimeGrouping.WEEK.value,
        TimeGrouping.MONTH.value,
    ]
    view.close()


def test_apply_trend_uses_selected_time_grouping(qapp) -> None:
    view = _build_view()
    overview = view._overview_tab
    overview.trend_chart = cast(Any, _ChartCapture())
    overview.time_grouping.setCurrentIndex(overview.time_grouping.findData(TimeGrouping.WEEK.value))

    overview._apply_trend(
        rows=[
            {"day": "2026-04-20", "total": 1, "positives": 1},
            {"day": "2026-04-21", "total": 99, "positives": 0},
        ],
        request=AnalyticsSearchRequest(date_from=date(2026, 4, 20), date_to=date(2026, 4, 26)),
    )

    assert cast(_ChartCapture, overview.trend_chart).items == [("2026-W17", 1.0)]
    view.close()


def test_time_grouping_change_refreshes_dashboard_and_keeps_selected_mode(qapp) -> None:
    class _AnalyticsGroupingStub(_AnalyticsServiceStub):
        def __init__(self) -> None:
            self.trend_calls = 0

        def get_trend_by_day(
            self,
            date_from: date | None,
            date_to: date | None,
            patient_category: str | None = None,
        ) -> list[dict[str, Any]]:
            _ = (date_to, patient_category)
            self.trend_calls += 1
            assert date_from is not None
            return [{"day": date_from.isoformat(), "total": 1, "positives": 1}]

    service = _AnalyticsGroupingStub()
    view = AnalyticsViewV2(
        analytics_service=cast(Any, service),
        reference_service=cast(Any, _ReferenceServiceStub()),
        saved_filter_service=cast(Any, _SavedFilterServiceStub()),
        reporting_service=cast(Any, _ReportingServiceStub()),
        session=_session_context(),
    )
    overview = view._overview_tab
    overview.trend_chart = cast(Any, _ChartCapture())
    overview._last_request = AnalyticsSearchRequest(date_from=date(2026, 1, 1), date_to=date(2026, 3, 31))

    overview.time_grouping.setCurrentIndex(overview.time_grouping.findData(TimeGrouping.WEEK.value))

    assert service.trend_calls == 1
    assert overview.time_grouping.currentData() == TimeGrouping.WEEK.value
    assert cast(_ChartCapture, overview.trend_chart).items[0][0] == "2026-W01"
    view.close()


def test_filter_payload_applies_dates_and_department(qapp) -> None:
    view = _build_view()
    filter_bar = view._filter_bar

    filter_bar.set_request_payload(
        {
            "date_from": "01.04.2026",
            "date_to": "03.04.2026",
            "department_id": 1,
        }
    )

    request = filter_bar.request()
    assert request.date_from == date(2026, 4, 1)
    assert request.date_to == date(2026, 4, 3)
    assert request.department_id == 1
    view.close()


def test_filter_payload_preserves_text_fields(qapp) -> None:
    view = _build_view()
    filter_bar = view._filter_bar

    filter_bar.set_request_payload({"patient_name": "Иванов", "lab_no": "LAB-1", "search_text": "E. coli"})
    payload = filter_bar.request_payload()

    assert payload["patient_name"] == "Иванов"
    assert payload["lab_no"] == "LAB-1"
    assert payload["search_text"] == "E. coli"
    view.close()


def test_report_history_table_is_read_only() -> None:
    view = _build_view()

    assert view._reports_tab.report_history_table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    view.close()


def test_analytics_view_initializes_current_month_and_populates_charts(qapp) -> None:
    current_date = cast(date, QDate.currentDate().toPython())

    class _AnalyticsStartupStub(_AnalyticsServiceStub):
        def get_aggregates(self, request: AnalyticsSearchRequest) -> dict[str, Any]:
            assert request.date_from == date(current_date.year, current_date.month, 1)
            assert request.date_to == current_date
            return {
                "total": 4,
                "positives": 2,
                "positive_share": 0.5,
                "top_microbes": [("ECO - E. coli", 2), ("SAU - S. aureus", 1)],
                "total_microbe_isolations": 3,
            }

        def get_trend_by_day(
            self,
            date_from: date | None,
            date_to: date | None,
            patient_category: str | None = None,
        ) -> list[dict[str, Any]]:
            _ = patient_category
            assert date_from is not None
            assert date_to is not None
            return [
                {"day": date_from.isoformat(), "total": 2, "positives": 1},
                {"day": current_date.isoformat(), "total": 4, "positives": 2},
            ]

    view = AnalyticsViewV2(
        analytics_service=cast(Any, _AnalyticsStartupStub()),
        reference_service=cast(Any, _ReferenceServiceStub()),
        saved_filter_service=cast(Any, _SavedFilterServiceStub()),
        reporting_service=cast(Any, _ReportingServiceStub()),
        session=_session_context(),
    )
    view.show()
    view.activate_view()
    qapp.processEvents()
    overview = view._overview_tab
    filter_bar = view._filter_bar

    first_day = date(current_date.year, current_date.month, 1)
    assert filter_bar.quick_period.currentData() == "month"
    assert filter_bar.date_from.date().toPython() == first_day
    assert filter_bar.date_to.date().toPython() == current_date
    assert overview.summary_share.text() == "Доля: 50.0%"
    assert overview.chart._items == [("ECO - E. coli", 66.66666666666666), ("SAU - S. aureus", 33.33333333333333)]
    assert len(overview.trend_chart._items) == current_date.day
    assert overview.trend_chart._items[0][0] == first_day.strftime("%d.%m.%Y")
    assert overview.trend_chart._items[current_date.day - 1][1] == 50.0
    view.close()


def test_analytics_view_activate_view_refreshes_once(qapp) -> None:
    current_date = cast(date, QDate.currentDate().toPython())

    class _AnalyticsStartupStub(_AnalyticsServiceStub):
        def __init__(self) -> None:
            self.aggregate_calls = 0

        def get_aggregates(self, request: AnalyticsSearchRequest) -> dict[str, Any]:
            self.aggregate_calls += 1
            assert request.date_from == date(current_date.year, current_date.month, 1)
            assert request.date_to == current_date
            return {
                "total": 4,
                "positives": 2,
                "positive_share": 0.5,
                "top_microbes": [("ECO - E. coli", 2), ("SAU - S. aureus", 1)],
                "total_microbe_isolations": 3,
            }

        def get_trend_by_day(
            self,
            date_from: date | None,
            date_to: date | None,
            patient_category: str | None = None,
        ) -> list[dict[str, Any]]:
            _ = patient_category
            assert date_from is not None
            assert date_to is not None
            return [
                {"day": date_from.isoformat(), "total": 2, "positives": 1},
                {"day": current_date.isoformat(), "total": 4, "positives": 2},
            ]

    service = _AnalyticsStartupStub()
    view = AnalyticsViewV2(
        analytics_service=cast(Any, service),
        reference_service=cast(Any, _ReferenceServiceStub()),
        saved_filter_service=cast(Any, _SavedFilterServiceStub()),
        reporting_service=cast(Any, _ReportingServiceStub()),
        session=_session_context(),
    )
    view.show()
    view.activate_view()
    view.activate_view()
    qapp.processEvents()
    overview = view._overview_tab

    assert service.aggregate_calls == 1
    assert overview.summary_share.text().endswith("50.0%")
    assert overview.chart._items == [("ECO - E. coli", 66.66666666666666), ("SAU - S. aureus", 33.33333333333333)]
    assert overview.trend_chart._items[0][0] == date(current_date.year, current_date.month, 1).strftime("%d.%m.%Y")
    assert overview.trend_chart._items[current_date.day - 1][1] == 50.0
    view.close()
