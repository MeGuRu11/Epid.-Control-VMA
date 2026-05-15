from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.ui.analytics.view_utils import calculate_compare_window

if TYPE_CHECKING:
    from app.application.dto.analytics_dto import AnalyticsSearchRequest
    from app.application.services.analytics_service import AnalyticsService
    from app.application.services.reference_service import ReferenceService
    from app.application.services.reporting_service import ReportingService
    from app.application.services.saved_filter_service import SavedFilterService


@dataclass
class AnalyticsController:
    analytics_service: AnalyticsService
    reference_service: ReferenceService
    saved_filter_service: SavedFilterService
    reporting_service: ReportingService

    def clear_cache(self) -> None:
        self.analytics_service.clear_cache()

    def search(self, request: AnalyticsSearchRequest) -> list[Any]:
        return self.analytics_service.search_samples(request)

    def get_aggregates(self, request: AnalyticsSearchRequest) -> dict[str, Any]:
        return self.analytics_service.get_aggregates(request)

    def get_ismp_metrics(self, request: AnalyticsSearchRequest) -> dict[str, Any]:
        return self.analytics_service.get_ismp_metrics(
            request.date_from,
            request.date_to,
            request.department_id,
        )

    def get_ismp_by_department(self, request: AnalyticsSearchRequest) -> list[tuple[str, int]]:
        return self.analytics_service.get_ismp_by_department(request.date_from, request.date_to)

    def get_department_summary(self, request: AnalyticsSearchRequest) -> list[dict[str, Any]]:
        return self.analytics_service.get_department_summary(
            request.date_from,
            request.date_to,
            patient_category=request.patient_category,
        )

    def get_trend(self, request: AnalyticsSearchRequest) -> list[dict[str, Any]]:
        return self.analytics_service.get_trend_by_day(
            request.date_from,
            request.date_to,
            patient_category=request.patient_category,
        )

    def compare_periods(self, request: AnalyticsSearchRequest, compare_days: int) -> dict[str, Any] | None:
        if request.date_to is None:
            return None
        current_from, current_to, prev_from, prev_to = calculate_compare_window(request.date_to, compare_days)
        return self.analytics_service.compare_periods(
            current_from=current_from,
            current_to=current_to,
            prev_from=prev_from,
            prev_to=prev_to,
            patient_category=request.patient_category,
        )

    def get_heatmap_data(
        self,
        request: AnalyticsSearchRequest,
        top_n: int = 10,
    ) -> tuple[dict[str, dict[str, int]], list[str]]:
        rows = self.search(request)
        matrix: dict[str, dict[str, int]] = {}
        dept_totals: dict[str, int] = {}
        micro_totals: dict[str, int] = {}

        for row in rows:
            if row.growth_flag != 1 or not row.department_name or not row.microorganism:
                continue
            dept = str(row.department_name)
            micro = str(row.microorganism)
            dept_map = matrix.setdefault(dept, {})
            dept_map[micro] = dept_map.get(micro, 0) + 1
            dept_totals[dept] = dept_totals.get(dept, 0) + 1
            micro_totals[micro] = micro_totals.get(micro, 0) + 1

        top_depts = sorted(dept_totals, key=dept_totals.__getitem__, reverse=True)[:top_n]
        top_micros = sorted(micro_totals, key=micro_totals.__getitem__, reverse=True)[:top_n]
        return (
            {
                dept: {micro: matrix[dept].get(micro, 0) for micro in top_micros}
                for dept in top_depts
            },
            top_micros,
        )

    def get_resistance_data(
        self,
        request: AnalyticsSearchRequest,
        top_n: int = 10,
    ) -> dict[str, dict[str, dict[str, int]]]:
        rows = self.search(request)
        matrix: dict[str, dict[str, dict[str, int]]] = {}
        micro_totals: dict[str, int] = {}

        for row in rows:
            if not row.microorganism or not row.antibiotic or not row.ris:
                continue
            ris = str(row.ris).upper()
            if ris not in {"S", "I", "R"}:
                continue
            micro = str(row.microorganism)
            antibiotic = str(row.antibiotic)
            micro_map = matrix.setdefault(micro, {})
            cell = micro_map.setdefault(antibiotic, {"S": 0, "I": 0, "R": 0, "total": 0})
            cell[ris] += 1
            cell["total"] += 1
            micro_totals[micro] = micro_totals.get(micro, 0) + 1

        top_micros = sorted(micro_totals, key=micro_totals.__getitem__, reverse=True)[:top_n]
        return {micro: matrix[micro] for micro in top_micros if micro in matrix}

    def list_saved_filters(self) -> list[Any]:
        return self.saved_filter_service.list_filters("analytics")

    def save_filter(self, name: str, request_payload: dict[str, object], actor_id: int) -> Any:
        return self.saved_filter_service.save_filter(
            filter_type="analytics",
            name=name,
            payload=request_payload,
            actor_id=actor_id,
        )

    def delete_filter(self, filter_id: int, actor_id: int) -> Any:
        return self.saved_filter_service.delete_filter(filter_id, actor_id)

    def load_report_history(
        self,
        *,
        report_type: str | None = None,
        query: str | None = None,
        verify_hash: bool = False,
    ) -> list[Any]:
        return self.reporting_service.list_report_runs(
            limit=100,
            report_type=report_type,
            query=query,
            verify_hash=verify_hash,
        )

    def verify_report_run(self, report_run_id: int) -> dict[str, Any]:
        return self.reporting_service.verify_report_run(report_run_id)

    def export_xlsx(self, request: AnalyticsSearchRequest, file_path: str, actor_id: int) -> dict[str, Any]:
        return self.reporting_service.export_analytics_xlsx(
            request=request,
            file_path=file_path,
            actor_id=actor_id,
        )

    def export_pdf(self, request: AnalyticsSearchRequest, file_path: str, actor_id: int) -> dict[str, Any]:
        return self.reporting_service.export_analytics_pdf(
            request=request,
            file_path=file_path,
            actor_id=actor_id,
        )
