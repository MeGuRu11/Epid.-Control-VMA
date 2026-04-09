from __future__ import annotations

from calendar import monthrange
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any, cast

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.dto.auth_dto import SessionContext
from app.ui.analytics.analytics_view import AnalyticsSearchView


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
    assert view.top_table.item(0, 0).text() == "ECO - E. coli"
    assert view.top_table.item(0, 1).text() == "3"
    assert view.top_table.item(0, 2).text() == "75.0%"
    assert view.top_table.item(1, 2).text() == "25.0%"
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


def test_analytics_view_initializes_current_month_and_populates_charts(qapp, monkeypatch) -> None:
    current_date = datetime.now(tz=UTC).date()

    class _AnalyticsStartupStub(_AnalyticsServiceStub):
        def get_aggregates(self, request: AnalyticsSearchRequest) -> dict[str, Any]:
            assert request.date_from == date(current_date.year, current_date.month, 1)
            assert request.date_to == date(current_date.year, current_date.month, monthrange(current_date.year, current_date.month)[1])
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
        else:
            if on_success is not None:
                on_success(result)
        finally:
            if on_finished is not None:
                on_finished()
        return None

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
    last_day = date(current_date.year, current_date.month, monthrange(current_date.year, current_date.month)[1])
    assert view.quick_period.currentData() == "month"
    assert view.date_from.date().toPython() == first_day
    assert view.date_to.date().toPython() == last_day
    assert view.summary_share.text() == "Доля: 50.0%"
    assert view.chart._items == [("ECO - E. coli", 66.66666666666666), ("SAU - S. aureus", 33.33333333333333)]
    assert len(view.trend_chart._items) == last_day.day
    assert view.trend_chart._items[0][0] == first_day.strftime("%d.%m.%Y")
    assert view.trend_chart._items[current_date.day - 1][1] == 50.0
    view.close()
