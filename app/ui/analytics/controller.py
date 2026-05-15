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
