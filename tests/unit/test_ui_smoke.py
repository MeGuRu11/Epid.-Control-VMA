from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from app.application.dto.auth_dto import SessionContext
from app.container import Container
from app.ui.analytics.analytics_view import AnalyticsSearchView
from app.ui.emz.emz_form import EmzForm
from app.ui.sanitary.sanitary_history import SanitaryHistoryDialog


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


class _SanitaryServiceStub:
    def list_samples_by_department(self, _department_id: int) -> list[SimpleNamespace]:
        return []


def _session_context() -> SessionContext:
    return SessionContext(user_id=1, login="tester", role="admin")


def test_analytics_view_smoke(qapp) -> None:
    reference_service = _ReferenceServiceStub()
    view = AnalyticsSearchView(
        analytics_service=cast(Any, _AnalyticsServiceStub()),
        reference_service=cast(Any, reference_service),
        saved_filter_service=cast(Any, _SavedFilterServiceStub()),
        reporting_service=cast(Any, _ReportingServiceStub()),
        session=_session_context(),
    )
    view.show()
    qapp.processEvents()

    assert view.report_history_table.rowCount() == 0
    assert view.summary_total.text().startswith("Итого:")
    view.close()


def test_emz_form_smoke(qapp) -> None:
    reference_service = _ReferenceServiceStub()
    container = cast(Container, SimpleNamespace(reference_service=reference_service))
    view = EmzForm(container=container, session=_session_context())
    view.show()
    qapp.processEvents()

    assert view.department_combo.count() >= 1
    assert view.diagnosis_table.rowCount() >= 1
    view.close()


def test_sanitary_history_smoke(qapp) -> None:
    dialog = SanitaryHistoryDialog(
        sanitary_service=cast(Any, _SanitaryServiceStub()),
        reference_service=cast(Any, _ReferenceServiceStub()),
        department_id=1,
        department_name="Тестовое отделение",
        actor_id=1,
    )
    dialog.show()
    qapp.processEvents()

    assert dialog.list_widget.count() >= 1
    assert dialog.page_label.text().startswith("Стр.")
    dialog.close()
