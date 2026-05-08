from __future__ import annotations

import time
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QAbstractItemView

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.dto.auth_dto import SessionContext
from app.ui.analytics.analytics_view import AnalyticsSearchView
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


class _ChartCapture:
    def __init__(self) -> None:
        self.items: list[tuple[str, float]] = []

    def update_data(self, items: list[tuple[str, float]] | tuple[tuple[str, float], ...] | Any) -> None:
        self.items = list(items)


def _session_context() -> SessionContext:
    return SessionContext(user_id=1, login="tester", role="admin")


def _build_view() -> AnalyticsSearchView:
    return AnalyticsSearchView(
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


def _layout_contains_widget(layout: Any, widget: Any) -> bool:
    return any(layout.itemAt(index).widget() is widget for index in range(layout.count()))


def _wait_until(qapp: Any, predicate: Any, timeout: float = 1.5) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Аналитический экран не обновился за ожидаемое время")


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
    view.chart = cast(Any, _ChartCapture())

    view._apply_search_results(
        rows=[],
        agg={
            "total": 8,
            "positives": 4,
            "positive_share": 0.5,
            "top_microbes": [("ECO - E. coli", 3), ("SAU - S. aureus", 1)],
            "total_microbe_isolations": 4,
        },
    )

    assert view.summary_share.text() == "Доля: 50.0%"
    assert cast(_ChartCapture, view.chart).items == [
        ("ECO - E. coli", 75.0),
        ("SAU - S. aureus", 25.0),
    ]
    assert view.top_table.columnCount() == 3
    first_name_item = view.top_table.item(0, 0)
    first_count_item = view.top_table.item(0, 1)
    first_share_item = view.top_table.item(0, 2)
    second_share_item = view.top_table.item(1, 2)
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
    view.trend_chart = cast(Any, _ChartCapture())

    view._apply_trend(
        rows=[
            {"day": "2026-04-01", "total": 10, "positives": 5},
            {"day": "2026-04-03", "total": 4, "positives": 1},
        ],
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 3),
    )

    assert cast(_ChartCapture, view.trend_chart).items == [
        ("01.04.2026", 50.0),
        ("02.04.2026", 0.0),
        ("03.04.2026", 25.0),
    ]
    view.close()


def test_analytics_time_grouping_combo_is_visible_in_dashboard_controls(qapp) -> None:
    view = _build_view()
    view.show()
    qapp.processEvents()

    assert view.time_grouping.objectName() == "analyticsTimeGroupingCombo"
    assert view.time_grouping_label.text() == "Группировка"
    assert _layout_contains_widget(view.dashboard_controls_row, view.time_grouping_label)
    assert _layout_contains_widget(view.dashboard_controls_row, view.time_grouping)
    assert view.time_grouping.isVisible()
    assert view.time_grouping.currentData() == TimeGrouping.AUTO.value
    assert _combo_labels(view.time_grouping) == ["Авто", "Дни", "Недели", "Месяцы"]
    assert _combo_values(view.time_grouping) == [
        TimeGrouping.AUTO.value,
        TimeGrouping.DAY.value,
        TimeGrouping.WEEK.value,
        TimeGrouping.MONTH.value,
    ]
    view.close()


def test_analytics_compare_period_and_time_grouping_are_separate_controls(qapp) -> None:
    view = _build_view()

    assert view.compare_period is not view.time_grouping
    assert view.compare_period.objectName() == "analyticsComparePeriodCombo"
    assert view.compare_period_label.text() == "Период сравнения"
    assert _layout_contains_widget(view.dashboard_controls_row, view.compare_period)
    assert _layout_contains_widget(view.dashboard_controls_row, view.time_grouping)
    assert _combo_labels(view.compare_period) == ["Неделя", "Месяц"]
    assert _combo_values(view.compare_period) == [7, 30]
    assert _combo_labels(view.time_grouping) == ["Авто", "Дни", "Недели", "Месяцы"]
    assert _combo_values(view.time_grouping) == [
        TimeGrouping.AUTO.value,
        TimeGrouping.DAY.value,
        TimeGrouping.WEEK.value,
        TimeGrouping.MONTH.value,
    ]
    view.close()


def test_apply_trend_uses_selected_time_grouping(qapp) -> None:
    view = _build_view()
    view.trend_chart = cast(Any, _ChartCapture())
    view._set_time_grouping(TimeGrouping.WEEK, notify=False)

    view._apply_trend(
        rows=[
            {"day": "2026-04-20", "total": 1, "positives": 1},
            {"day": "2026-04-21", "total": 99, "positives": 0},
        ],
        date_from=date(2026, 4, 20),
        date_to=date(2026, 4, 26),
    )

    assert cast(_ChartCapture, view.trend_chart).items == [("2026-W17", 1.0)]
    view.close()


def test_time_grouping_change_refreshes_dashboard_and_keeps_selected_mode(qapp, monkeypatch) -> None:
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

    def _run_async_sync(
        _parent: Any,
        fn: Any,
        on_success: Any = None,
        on_error: Any = None,
        on_finished: Any = None,
    ) -> Any:
        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001
            if on_error is not None:
                on_error(exc)
            raise
        else:
            if on_success is not None:
                on_success(result)
        finally:
            if on_finished is not None:
                on_finished()
        return None

    service = _AnalyticsGroupingStub()
    monkeypatch.setattr("app.ui.analytics.analytics_view.run_async", _run_async_sync)
    view = AnalyticsSearchView(
        analytics_service=cast(Any, service),
        reference_service=cast(Any, _ReferenceServiceStub()),
        saved_filter_service=cast(Any, _SavedFilterServiceStub()),
        reporting_service=cast(Any, _ReportingServiceStub()),
        session=_session_context(),
    )
    view.trend_chart = cast(Any, _ChartCapture())
    view.date_from.setDate(QDate(2026, 1, 1))
    view.date_to.setDate(QDate(2026, 3, 31))

    view.time_grouping.setCurrentIndex(view.time_grouping.findData(TimeGrouping.WEEK.value))

    assert service.trend_calls == 1
    assert view.time_grouping.currentData() == TimeGrouping.WEEK.value
    assert cast(_ChartCapture, view.trend_chart).items[0][0] == "2026-W01"
    view.close()


def test_filter_payload_restores_missing_time_grouping_as_auto(qapp) -> None:
    view = _build_view()
    view._set_time_grouping(TimeGrouping.MONTH, notify=False)

    view._apply_filter_payload({})

    assert view.time_grouping.currentData() == TimeGrouping.AUTO.value
    view.close()


def test_filter_payload_preserves_time_grouping(qapp) -> None:
    view = _build_view()
    view._set_time_grouping(TimeGrouping.WEEK, notify=False)

    payload = view._collect_filter_payload()
    view._apply_filter_payload({"time_grouping": TimeGrouping.MONTH.value})

    assert payload["time_grouping"] == TimeGrouping.WEEK.value
    assert view.time_grouping.currentData() == TimeGrouping.MONTH.value
    view.close()


def test_report_history_table_is_read_only() -> None:
    view = _build_view()

    assert view.report_history_table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    view.close()


def test_analytics_view_initializes_current_month_and_populates_charts(qapp, monkeypatch) -> None:
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

    def _run_async_sync(
        _parent: Any,
        fn: Any,
        on_success: Any = None,
        on_error: Any = None,
        on_finished: Any = None,
    ) -> Any:
        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001
            if on_error is not None:
                on_error(exc)
            raise
        else:
            if on_success is not None:
                on_success(result)
        finally:
            if on_finished is not None:
                on_finished()
        return None

    monkeypatch.setattr("app.ui.analytics.analytics_view.show_error", lambda *_a, **_kw: None)
    monkeypatch.setattr("app.ui.analytics.analytics_view.run_async", _run_async_sync)

    view = AnalyticsSearchView(
        analytics_service=cast(Any, _AnalyticsStartupStub()),
        reference_service=cast(Any, _ReferenceServiceStub()),
        saved_filter_service=cast(Any, _SavedFilterServiceStub()),
        reporting_service=cast(Any, _ReportingServiceStub()),
        session=_session_context(),
    )
    view.show()
    qapp.processEvents()

    first_day = date(current_date.year, current_date.month, 1)
    assert view.quick_period.currentData() == "month"
    assert view.date_from.date().toPython() == first_day
    assert view.date_to.date().toPython() == current_date
    assert view.summary_share.text() == "Доля: 50.0%"
    assert view.chart._items == [("ECO - E. coli", 66.66666666666666), ("SAU - S. aureus", 33.33333333333333)]
    assert len(view.trend_chart._items) == current_date.day
    assert view.trend_chart._items[0][0] == first_day.strftime("%d.%m.%Y")
    assert view.trend_chart._items[current_date.day - 1][1] == 50.0
    view.close()


def test_analytics_view_initializes_current_month_with_real_async(qapp) -> None:
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

    view = AnalyticsSearchView(
        analytics_service=cast(Any, _AnalyticsStartupStub()),
        reference_service=cast(Any, _ReferenceServiceStub()),
        saved_filter_service=cast(Any, _SavedFilterServiceStub()),
        reporting_service=cast(Any, _ReportingServiceStub()),
        session=_session_context(),
    )
    view.show()

    _wait_until(qapp, lambda: len(view.trend_chart._items) == current_date.day)

    first_day = date(current_date.year, current_date.month, 1)
    assert view.quick_period.currentData() == "month"
    assert view.date_from.date().toPython() == first_day
    assert view.date_to.date().toPython() == current_date
    assert view.summary_share.text().endswith("50.0%")
    assert view.chart._items == [("ECO - E. coli", 66.66666666666666), ("SAU - S. aureus", 33.33333333333333)]
    assert view.trend_chart._items[0][0] == first_day.strftime("%d.%m.%Y")
    assert view.trend_chart._items[current_date.day - 1][1] == 50.0
    view.close()
