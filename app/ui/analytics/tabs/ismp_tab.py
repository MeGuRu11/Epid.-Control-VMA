from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.analytics.view_utils import make_section_frame
from app.ui.analytics.widgets.donut_chart import DonutChart, IsmpDepartmentBar
from app.ui.analytics.widgets.empty_state import CurrentWidgetStack, make_inline_placeholder
from app.ui.analytics.widgets.kpi_card import KpiCard
from app.ui.widgets.table_utils import resize_columns_to_content, set_table_read_only

if TYPE_CHECKING:
    from app.application.dto.analytics_dto import AnalyticsSearchRequest
    from app.ui.analytics.controller import AnalyticsController


class IsmpTab(QWidget):
    def __init__(self, controller: AnalyticsController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._last_request: AnalyticsSearchRequest | None = None
        self._build_ui()

    def refresh(self, request: AnalyticsSearchRequest) -> None:
        self._last_request = request
        data = self.controller.get_ismp_metrics(request)
        has_data = int(data.get("ismp_cases", 0)) > 0
        department_data = self.controller.get_ismp_by_department(request)
        self._update_kpi(data)
        self._update_donut(data)
        self._dept_bar.set_data(department_data)
        self._donut_stack.setCurrentWidget(self._donut if has_data else self._donut_empty)
        self._dept_stack.setCurrentWidget(
            self._dept_bar if has_data and department_data else self._dept_empty
        )

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._kpi_total = KpiCard("Госпитализаций", "Г", "neutral", "neutral", show_sparkline=False)
        self._kpi_ismp = KpiCard("С ИСМП", "И", "negative", "negative", show_sparkline=False)
        self._kpi_inc = KpiCard("Инцидентность ‰", "‰", "calc", "negative", show_sparkline=False)
        self._kpi_dens = KpiCard("Плотность ‰ к.дн.", "П", "calc", "negative", show_sparkline=False)
        self._kpi_prev = KpiCard("Превалентность", "%", "calc", "negative", show_sparkline=False)

        self._content_widget = QWidget()
        content_layout = QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(12)
        for column, card in enumerate((self._kpi_total, self._kpi_ismp, self._kpi_inc, self._kpi_dens, self._kpi_prev)):
            kpi_grid.addWidget(card, 0, column)
            kpi_grid.setColumnStretch(column, 1)
        content_layout.addLayout(kpi_grid)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        donut_box, donut_layout = make_section_frame("Распределение по типам ИСМП")
        self._donut_stack = CurrentWidgetStack()
        self._donut = DonutChart()
        self._donut_stack.addWidget(self._donut)
        self._donut_empty = make_inline_placeholder("Случаев ИСМП за период не зарегистрировано")
        self._donut_stack.addWidget(self._donut_empty)
        self._donut_stack.setCurrentWidget(self._donut_empty)
        donut_layout.addWidget(self._donut_stack)
        charts_row.addWidget(donut_box, 1)

        department_box, department_layout = make_section_frame("По отделениям")
        self._dept_stack = CurrentWidgetStack()
        self._dept_bar = IsmpDepartmentBar()
        self._dept_stack.addWidget(self._dept_bar)
        self._dept_empty = make_inline_placeholder("Случаев ИСМП за период не зарегистрировано")
        self._dept_stack.addWidget(self._dept_empty)
        self._dept_stack.setCurrentWidget(self._dept_empty)
        department_layout.addWidget(self._dept_stack)
        charts_row.addWidget(department_box, 1)

        content_layout.addLayout(charts_row)

        table_box, table_layout = make_section_frame("Типы ИСМП")
        self.ismp_table = QTableWidget(0, 2)
        self.ismp_table.setHorizontalHeaderLabels(["Тип ИСМП", "Количество"])
        self.ismp_table.horizontalHeader().setStretchLastSection(True)
        self.ismp_table.verticalHeader().setVisible(False)
        self.ismp_table.setAlternatingRowColors(True)
        self.ismp_table.setMinimumHeight(140)
        set_table_read_only(self.ismp_table)
        table_layout.addWidget(self.ismp_table)
        content_layout.addWidget(table_box)
        layout.addWidget(self._content_widget)
        layout.addStretch()

    def _update_kpi(self, data: dict[str, Any]) -> None:
        self._kpi_total.set_value(str(int(data.get("total_cases", 0))))
        self._kpi_ismp.set_value(str(int(data.get("ismp_cases", 0))))
        self._kpi_inc.set_value(f"{float(data.get('incidence', 0.0)):.1f}")
        self._kpi_dens.set_value(f"{float(data.get('incidence_density', 0.0)):.1f}")
        self._kpi_prev.set_value(f"{float(data.get('prevalence', 0.0)):.1f}%")

    def _update_donut(self, data: dict[str, Any]) -> None:
        items = self._type_items(data.get("by_type") or [])
        self._donut.set_data(items)

        self.ismp_table.clearContents()
        self.ismp_table.setRowCount(len(items))
        for row_index, (name, count) in enumerate(items):
            self.ismp_table.setItem(row_index, 0, QTableWidgetItem(str(name)))
            self.ismp_table.setItem(row_index, 1, QTableWidgetItem(str(count)))
        resize_columns_to_content(self.ismp_table)

    def _type_items(self, by_type: object) -> list[tuple[str, int]]:
        if isinstance(by_type, dict):
            return [(str(name), int(count)) for name, count in by_type.items()]
        if isinstance(by_type, list):
            items: list[tuple[str, int]] = []
            for entry in by_type:
                if not isinstance(entry, dict):
                    continue
                name = str(entry.get("type") or "")
                count = int(entry.get("count") or 0)
                if name:
                    items.append((name, count))
            return items
        return []
