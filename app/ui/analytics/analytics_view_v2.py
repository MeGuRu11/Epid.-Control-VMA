from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

from app.ui.analytics.controller import AnalyticsController
from app.ui.analytics.filter_bar import FilterBar
from app.ui.analytics.tabs.ismp_tab import IsmpTab
from app.ui.analytics.tabs.microbiology_tab import MicrobiologyTab
from app.ui.analytics.tabs.overview_tab import OverviewTab
from app.ui.analytics.tabs.reports_tab import ReportsTab
from app.ui.analytics.tabs.search_tab import SearchTab

if TYPE_CHECKING:
    from app.application.dto.analytics_dto import AnalyticsSearchRequest
    from app.application.dto.auth_dto import SessionContext
    from app.application.services.analytics_service import AnalyticsService
    from app.application.services.reference_service import ReferenceService
    from app.application.services.reporting_service import ReportingService
    from app.application.services.saved_filter_service import SavedFilterService


class AnalyticsViewV2(QWidget):
    def __init__(
        self,
        analytics_service: AnalyticsService,
        reference_service: ReferenceService,
        saved_filter_service: SavedFilterService,
        reporting_service: ReportingService,
        session: SessionContext,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.session = session
        self._default_analytics_loaded = False
        self._current_request: AnalyticsSearchRequest | None = None
        self._controller = AnalyticsController(
            analytics_service=analytics_service,
            reference_service=reference_service,
            saved_filter_service=saved_filter_service,
            reporting_service=reporting_service,
        )
        self._build_ui(reference_service)

    def set_session(self, session: SessionContext) -> None:
        self.session = session
        self._search_tab.set_session(session)

    def activate_view(self) -> None:
        if self._default_analytics_loaded:
            return
        self._default_analytics_loaded = True
        self._current_request = self._filter_bar.request()
        self._refresh_current_tab()

    def refresh_references(self) -> None:
        self._filter_bar.reload_references()

    def _build_ui(self, reference_service: ReferenceService) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Поиск и аналитика")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        self._filter_bar = FilterBar(reference_service=reference_service)
        self._filter_bar.filters_changed.connect(self._on_filters_changed)
        layout.addWidget(self._filter_bar)

        self._tabs = QTabWidget()
        self._overview_tab = OverviewTab(self._controller)
        self._microbiology_tab = MicrobiologyTab(self._controller)
        self._ismp_tab = IsmpTab(self._controller)
        self._search_tab = SearchTab(self._controller, self.session)
        self._reports_tab = ReportsTab(self._controller)
        self._search_tab.saved_filter_applied.connect(self._filter_bar.set_request_payload)

        self._tabs.addTab(self._overview_tab, "Обзор")
        self._tabs.addTab(self._microbiology_tab, "Микробиология")
        self._tabs.addTab(self._ismp_tab, "ИСМП")
        self._tabs.addTab(self._search_tab, "Поиск")
        self._tabs.addTab(self._reports_tab, "Отчёты")
        self._tabs.currentChanged.connect(lambda _index: self._refresh_current_tab())
        layout.addWidget(self._tabs)

    def _on_filters_changed(self, request: AnalyticsSearchRequest) -> None:
        self._current_request = request
        if self._default_analytics_loaded:
            self._refresh_current_tab()

    def _refresh_current_tab(self) -> None:
        current = self._tabs.currentWidget()
        if current is self._reports_tab:
            self._reports_tab.refresh()
            return
        request = self._current_request or self._filter_bar.request()
        if current is self._search_tab:
            self._search_tab.run_search(request)
            return
        if hasattr(current, "refresh"):
            current.refresh(request)
