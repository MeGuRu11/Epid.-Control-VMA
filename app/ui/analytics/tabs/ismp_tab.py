from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.analytics.widgets.donut_chart import DonutChart, IsmpDepartmentBar
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
        department_data = self.controller.get_ismp_by_department(request)
        self._update_kpi(data)
        self._update_donut(data)
        self._dept_bar.set_data(department_data)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._kpi_total = KpiCard("Госпитализаций", "Г", "neutral", "neutral", show_sparkline=False)
        self._kpi_ismp = KpiCard("С ИСМП", "И", "negative", "negative", show_sparkline=False)
        self._kpi_inc = KpiCard("Инцидентность ‰", "‰", "calc", "negative", show_sparkline=False)
        self._kpi_dens = KpiCard("Плотность ‰ к.дн.", "П", "calc", "negative", show_sparkline=False)
        self._kpi_prev = KpiCard("Превалентность", "%", "calc", "negative", show_sparkline=False)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        for card in (self._kpi_total, self._kpi_ismp, self._kpi_inc, self._kpi_dens, self._kpi_prev):
            kpi_row.addWidget(card)
        layout.addLayout(kpi_row)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        donut_box = QGroupBox("Распределение по типам ИСМП")
        donut_layout = QVBoxLayout(donut_box)
        self._donut = DonutChart()
        donut_layout.addWidget(self._donut)
        charts_row.addWidget(donut_box, 1)

        department_box = QGroupBox("По отделениям")
        department_layout = QVBoxLayout(department_box)
        self._dept_bar = IsmpDepartmentBar()
        department_layout.addWidget(self._dept_bar)
        charts_row.addWidget(department_box, 1)

        layout.addLayout(charts_row)

        table_box = QGroupBox("Типы ИСМП")
        table_layout = QVBoxLayout(table_box)
        self.ismp_table = QTableWidget(0, 2)
        self.ismp_table.setHorizontalHeaderLabels(["Тип ИСМП", "Количество"])
        self.ismp_table.horizontalHeader().setStretchLastSection(True)
        self.ismp_table.verticalHeader().setVisible(False)
        self.ismp_table.setAlternatingRowColors(True)
        self.ismp_table.setMinimumHeight(140)
        set_table_read_only(self.ismp_table)
        table_layout.addWidget(self.ismp_table)
        layout.addWidget(table_box)
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
