from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any, cast

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
    pass


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
