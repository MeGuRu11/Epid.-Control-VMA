from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PySide6.QtWidgets import QGroupBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.ui.analytics.charts import TopMicrobesChart
from app.ui.analytics.view_utils import build_top_microbe_chart_items
from app.ui.widgets.table_utils import resize_columns_to_content, set_table_read_only

if TYPE_CHECKING:
    from app.application.dto.analytics_dto import AnalyticsSearchRequest
    from app.ui.analytics.controller import AnalyticsController


class MicrobiologyTab(QWidget):
    def __init__(self, controller: AnalyticsController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def refresh(self, request: AnalyticsSearchRequest) -> None:
        agg = self.controller.get_aggregates(request)
        top_microbes = cast(list[tuple[str, int]], agg.get("top_microbes", []))
        total_microbe_isolations = int(
            agg.get("total_microbe_isolations") or sum(count for _name, count in top_microbes)
        )
        chart_items = build_top_microbe_chart_items(
            top_microbes,
            total_microbe_isolations=total_microbe_isolations,
        )
        self.chart.update_data(chart_items)
        self.top_table.clearContents()
        self.top_table.setRowCount(len(top_microbes))
        for idx, (name, count) in enumerate(top_microbes):
            self.top_table.setItem(idx, 0, QTableWidgetItem(name))
            self.top_table.setItem(idx, 1, QTableWidgetItem(str(count)))
            share = chart_items[idx][1] if idx < len(chart_items) else 0.0
            self.top_table.setItem(idx, 2, QTableWidgetItem(f"{share:.1f}%"))
        resize_columns_to_content(self.top_table)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        top_box = QGroupBox("Топ микроорганизмов")
        top_layout = QVBoxLayout(top_box)
        self.chart = TopMicrobesChart()
        self.chart.setMinimumHeight(340)
        top_layout.addWidget(self.chart)
        self.top_table = QTableWidget(0, 3)
        self.top_table.setHorizontalHeaderLabels(["Микроорганизм", "Количество", "Доля"])
        self.top_table.horizontalHeader().setStretchLastSection(True)
        self.top_table.verticalHeader().setVisible(False)
        self.top_table.setAlternatingRowColors(True)
        self.top_table.setMinimumHeight(220)
        set_table_read_only(self.top_table)
        top_layout.addWidget(self.top_table)
        layout.addWidget(top_box)
        layout.addStretch()
