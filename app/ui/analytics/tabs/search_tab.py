from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.analytics.view_utils import format_analytics_datetime
from app.ui.widgets.action_bar_layout import update_action_bar_direction
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import show_error, show_info, show_warning
from app.ui.widgets.table_utils import (
    connect_combo_autowidth,
    resize_columns_to_content,
    set_table_read_only,
)

if TYPE_CHECKING:
    from app.application.dto.analytics_dto import AnalyticsSearchRequest
    from app.application.dto.auth_dto import SessionContext
    from app.ui.analytics.controller import AnalyticsController

_COLLAPSED_ARROW = "▾"
_EXPANDED_ARROW = "▴"


class SearchTab(QWidget):
    saved_filter_applied = Signal(dict)

    def __init__(
        self,
        controller: AnalyticsController,
        session: SessionContext,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.session = session
        self._last_request: AnalyticsSearchRequest | None = None
        self._build_ui()
        self.load_saved_filters()

    def set_session(self, session: SessionContext) -> None:
        self.session = session

    def run_search(self, request: AnalyticsSearchRequest) -> None:
        self._last_request = request
        try:
            rows = self.controller.search(request)
            agg = self.controller.get_aggregates(request)
        except (LookupError, RuntimeError, ValueError, TypeError) as exc:
            show_error(self, str(exc))
            return
        self._apply_search_results(rows, agg)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self._build_saved_filters_section(layout)
        self._build_actions_row(layout)
        self._build_summary_row(layout)
        layout.addWidget(self._build_results_box())
        layout.addStretch()

    def _build_saved_filters_section(self, content_layout: QVBoxLayout) -> None:
        self.saved_filters_toggle = QPushButton(f"Фильтры {_COLLAPSED_ARROW}")
        self.saved_filters_toggle.setCheckable(True)
        compact_button(self.saved_filters_toggle)
        self.saved_filters_toggle.toggled.connect(self._toggle_saved_filters)
        content_layout.addWidget(self.saved_filters_toggle)

        self.saved_filters_container = QWidget()
        saved_container_layout = QVBoxLayout(self.saved_filters_container)
        saved_container_layout.setContentsMargins(0, 0, 0, 0)

        saved_box = QGroupBox("Сохранённые фильтры")
        saved_layout = QHBoxLayout(saved_box)
        self.saved_filter_select = QComboBox()
        self.saved_filter_select.addItem("Выбрать", None)
        connect_combo_autowidth(self.saved_filter_select)
        apply_filter_btn = QPushButton("Применить")
        compact_button(apply_filter_btn)
        apply_filter_btn.clicked.connect(self._apply_saved_filter)
        self.filter_name = QLineEdit()
        self.filter_name.setPlaceholderText("Название фильтра")
        save_filter_btn = QPushButton("Сохранить")
        compact_button(save_filter_btn)
        save_filter_btn.clicked.connect(self._save_filter)
        saved_layout.addWidget(QLabel("Фильтр"))
        saved_layout.addWidget(self.saved_filter_select)
        saved_layout.addWidget(apply_filter_btn)
        saved_layout.addWidget(QLabel("Название"))
        saved_layout.addWidget(self.filter_name)
        saved_layout.addWidget(save_filter_btn)
        saved_container_layout.addWidget(saved_box)
        self.saved_filters_container.setVisible(False)
        content_layout.addWidget(self.saved_filters_container)

    def _build_actions_row(self, content_layout: QVBoxLayout) -> None:
        self.search_btn = QPushButton("Поиск")
        self.search_btn.setObjectName("primaryButton")
        compact_button(self.search_btn)
        self.search_btn.clicked.connect(self._rerun_search)
        self._export_xlsx_btn = QPushButton("Экспорт XLSX")
        self._export_xlsx_btn.setObjectName("secondaryButton")
        compact_button(self._export_xlsx_btn)
        self._export_xlsx_btn.clicked.connect(self._export_xlsx)
        self._export_pdf_btn = QPushButton("Экспорт PDF")
        self._export_pdf_btn.setObjectName("secondaryButton")
        compact_button(self._export_pdf_btn)
        self._export_pdf_btn.clicked.connect(self._export_pdf)
        self._main_actions_bar = QWidget()
        self._main_actions_bar.setObjectName("sectionActionBar")
        self._main_actions_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._main_actions_bar)
        self._main_actions_layout.setContentsMargins(12, 8, 12, 8)
        self._main_actions_layout.setSpacing(10)

        self._main_export_group = QWidget()
        self._main_export_group.setObjectName("sectionActionGroup")
        export_layout = QHBoxLayout(self._main_export_group)
        export_layout.setContentsMargins(0, 0, 0, 0)
        export_layout.setSpacing(8)
        export_layout.addWidget(self._export_xlsx_btn)
        export_layout.addWidget(self._export_pdf_btn)

        self._main_search_group = QWidget()
        self._main_search_group.setObjectName("sectionActionGroup")
        search_layout = QHBoxLayout(self._main_search_group)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.addWidget(self.search_btn)

        self._main_actions_layout.addWidget(self._main_export_group)
        self._main_actions_layout.addStretch()
        self._main_actions_layout.addWidget(self._main_search_group)
        content_layout.addWidget(self._main_actions_bar)
        self._update_main_actions_layout()

    def _build_summary_row(self, content_layout: QVBoxLayout) -> None:
        summary_row = QHBoxLayout()
        summary_row.addWidget(QLabel("Сводка поиска:"))
        self.summary_total = QLabel("Итого: 0")
        self.summary_total.setObjectName("chipLabel")
        self.summary_positive = QLabel("Положительных: 0")
        self.summary_positive.setObjectName("chipLabel")
        self.summary_share = QLabel("Доля: 0%")
        self.summary_share.setObjectName("chipLabel")
        summary_row.addWidget(self.summary_total)
        summary_row.addWidget(self.summary_positive)
        summary_row.addWidget(self.summary_share)
        summary_row.addStretch()
        content_layout.addLayout(summary_row)

    def _build_results_box(self) -> QGroupBox:
        results_box = QGroupBox("Результаты")
        results_layout = QVBoxLayout(results_box)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Лаб. номер",
                "Пациент",
                "Категория",
                "Дата взятия",
                "Отделение",
                "Материал",
                "Микроорганизм",
                "Антибиотик",
            ]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(320)
        set_table_read_only(self.table)
        results_layout.addWidget(self.table)
        return results_box

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_main_actions_layout()

    def load_saved_filters(self) -> None:
        self.saved_filter_select.clear()
        self.saved_filter_select.addItem("Выбрать", None)
        try:
            filters = self.controller.list_saved_filters()
        except (LookupError, RuntimeError, ValueError, TypeError) as exc:
            show_error(self, str(exc))
            return
        for item in filters:
            self.saved_filter_select.addItem(str(item.name), str(item.payload_json))
        connect_combo_autowidth(self.saved_filter_select)

    def _apply_search_results(self, rows: list[Any], agg: dict[str, Any]) -> None:
        total = int(agg.get("total", 0))
        positives = int(agg.get("positives", 0))
        positive_share = float(agg.get("positive_share", 0.0))
        self.summary_total.setText(f"Итого: {total}")
        self.summary_positive.setText(f"Положительных: {positives}")
        self.summary_share.setText(f"Доля: {positive_share * 100:.1f}%")

        display_rows = rows[:1000]
        if len(rows) > 1000:
            show_warning(self, "Показаны первые 1000 записей. Для получения всех данных используйте экспорт.")

        self.table.clearContents()
        self.table.setRowCount(len(display_rows))
        for i, row in enumerate(display_rows):
            values = [
                getattr(row, "lab_sample_id", ""),
                getattr(row, "lab_no", ""),
                getattr(row, "patient_name", ""),
                getattr(row, "patient_category", "") or "",
                format_analytics_datetime(getattr(row, "taken_at", None)),
                getattr(row, "department_name", "") or "",
                getattr(row, "material_type", "") or "",
                getattr(row, "microorganism", "") or "",
                getattr(row, "antibiotic", "") or "",
            ]
            for column, value in enumerate(values):
                self.table.setItem(i, column, QTableWidgetItem(str(value)))
        resize_columns_to_content(self.table)

    def _update_main_actions_layout(self) -> None:
        update_action_bar_direction(
            self._main_actions_layout,
            self._main_actions_bar,
            [self._main_export_group, self._main_search_group],
        )

    def _toggle_saved_filters(self, checked: bool) -> None:
        self.saved_filters_container.setVisible(checked)
        self.saved_filters_toggle.setText(f"Фильтры {_EXPANDED_ARROW if checked else _COLLAPSED_ARROW}")

    def _rerun_search(self) -> None:
        if self._last_request is None:
            show_warning(self, "Сначала задайте параметры поиска.")
            return
        self.run_search(self._last_request)

    def _save_filter(self) -> None:
        name = self.filter_name.text().strip()
        if self._last_request is None:
            show_warning(self, "Сначала задайте параметры поиска.")
            return
        payload = self._last_request.model_dump(mode="json", exclude_none=True)
        try:
            self.controller.save_filter(name, payload, self.session.user_id)
        except ValueError as exc:
            show_warning(self, str(exc))
            return
        except (LookupError, RuntimeError, TypeError) as exc:
            show_error(self, str(exc))
            return
        self.load_saved_filters()
        self.filter_name.clear()
        show_info(self, "Фильтр сохранён")

    def _apply_saved_filter(self) -> None:
        payload_json = self.saved_filter_select.currentData()
        if not payload_json:
            show_warning(self, "Выберите сохранённый фильтр")
            return
        try:
            payload = json.loads(payload_json)
        except (TypeError, ValueError) as exc:
            show_error(self, f"Невозможно прочитать фильтр: {exc}")
            return
        if isinstance(payload, dict):
            self.saved_filter_applied.emit(payload)

    def _export_xlsx(self) -> None:
        self._export("xlsx")

    def _export_pdf(self) -> None:
        self._export("pdf")

    def _export(self, kind: str) -> None:
        if self._last_request is None:
            show_warning(self, "Сначала выполните поиск.")
            return
        from PySide6.QtWidgets import QFileDialog

        from app.ui.settings.export_paths import compose_save_path

        if kind == "xlsx":
            title = "Экспорт XLSX"
            default_path = compose_save_path("excel", "analytics_report.xlsx")
            filter_text = "Excel (*.xlsx)"
            exporter = self.controller.export_xlsx
        else:
            title = "Экспорт PDF"
            default_path = compose_save_path("pdf", "analytics_report.pdf")
            filter_text = "PDF (*.pdf)"
            exporter = self.controller.export_pdf

        path, _ = QFileDialog.getSaveFileName(self, title, default_path, filter_text)
        if not path:
            return
        try:
            result = exporter(self._last_request, path, self.session.user_id)
        except (LookupError, RuntimeError, ValueError, TypeError) as exc:
            show_error(self, str(exc))
            return
        show_info(self, f"Экспорт завершён: {result.get('count', 0)} строк")
