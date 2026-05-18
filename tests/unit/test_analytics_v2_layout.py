from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from PySide6.QtWidgets import QLabel, QSizePolicy

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
    def clear_cache(self) -> None:
        return None

    def search_samples(self, _request: object) -> list[object]:
        return []

    def get_aggregates(self, _request: object) -> dict[str, object]:
        return {
            "total": 0,
            "positives": 0,
            "positive_share": 0.0,
            "top_microbes": [],
            "total_microbe_isolations": 0,
        }

    def get_ismp_metrics(self, _date_from: object, _date_to: object, _department_id: object) -> dict[str, object]:
        return {}

    def get_ismp_by_department(self, _date_from: object, _date_to: object) -> list[tuple[str, int]]:
        return []

    def get_department_summary(
        self,
        _date_from: object,
        _date_to: object,
        patient_category: str | None = None,
    ) -> list[dict[str, object]]:
        _ = patient_category
        return []

    def get_trend_by_day(
        self,
        _date_from: object,
        _date_to: object,
        patient_category: str | None = None,
    ) -> list[dict[str, object]]:
        _ = patient_category
        return []

    def compare_periods(self, **_kwargs: object) -> dict[str, dict[str, float]]:
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

    def delete_filter(self, _filter_id: int, _actor_id: int) -> bool:
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

    def export_analytics_xlsx(self, _request: object, _file_path: str, _actor_id: int) -> dict[str, int]:
        return {"count": 0}

    def export_analytics_pdf(self, _request: object, _file_path: str, _actor_id: int) -> dict[str, int]:
        return {"count": 0}


def _build_view() -> Any:
    from app.ui.analytics.analytics_view_v2 import AnalyticsViewV2

    return AnalyticsViewV2(
        analytics_service=cast(Any, _AnalyticsServiceStub()),
        reference_service=cast(Any, _ReferenceServiceStub()),
        saved_filter_service=cast(Any, _SavedFilterServiceStub()),
        reporting_service=cast(Any, _ReportingServiceStub()),
        session=SessionContext(user_id=1, login="tester", role="admin"),
    )


def test_analytics_view_v2_title_and_filter_stay_compact_on_wide_view(qtbot: Any, qapp: Any) -> None:
    """Заголовок и filter-bar не забирают вертикальную высоту wide/maximized окна."""
    view = _build_view()
    qtbot.addWidget(view)
    view.resize(1707, 815)
    view.show()
    qapp.processEvents()

    title = view.findChild(QLabel, "pageTitle")
    assert title is not None
    assert title.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Preferred
    assert view._filter_bar.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Preferred
    assert title.height() <= title.sizeHint().height() + 8
    assert view._filter_bar.height() <= view._filter_bar.sizeHint().height() + 8


def test_analytics_view_v2_tabs_get_remaining_vertical_space(qtbot: Any) -> None:
    """QTabWidget получает stretch и является единственной растягиваемой зоной."""
    view = _build_view()
    qtbot.addWidget(view)

    layout = view.layout()
    tabs_index = layout.indexOf(view._tabs)

    assert tabs_index >= 0
    assert layout.stretch(tabs_index) > 0
    assert view._tabs.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Expanding
