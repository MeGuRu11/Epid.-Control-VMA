from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PySide6.QtWidgets import QGroupBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.ui.analytics.charts import TopMicrobesChart
from app.ui.analytics.view_utils import build_top_microbe_chart_items
from app.ui.analytics.widgets.heatmap import Heatmap
from app.ui.analytics.widgets.quick_filter_chips import QuickFilterChips
from app.ui.analytics.widgets.resistance_grid import ResistanceGrid
from app.ui.widgets.table_utils import resize_columns_to_content, set_table_read_only

if TYPE_CHECKING:
    from app.ui.analytics.controller import AnalyticsController


class MicrobiologyTab(QWidget):
    def __init__(self, controller: AnalyticsController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._last_request = AnalyticsSearchRequest()
        self._build_ui()

    def refresh(self, request: AnalyticsSearchRequest) -> None:
        self._last_request = request
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

        matrix, ordered_micros = self.controller.get_heatmap_data(request)
        self._heatmap.set_data(matrix, ordered_micros)

        resistance = self.controller.get_resistance_data(request)
        self._resistance_grid.set_data(resistance)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._chips = QuickFilterChips(
            base_request_getter=lambda: self._last_request,
            material_type_ids=self._material_type_ids(),
        )
        self._chips.filter_changed.connect(self.refresh)
        layout.addWidget(self._chips)

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

        heatmap_box = QGroupBox("Отделения × микроорганизмы")
        heatmap_layout = QVBoxLayout(heatmap_box)
        self._heatmap = Heatmap()
        self._heatmap.setMinimumHeight(260)
        self._heatmap.cell_clicked.connect(self._on_heatmap_cell_clicked)
        heatmap_layout.addWidget(self._heatmap)
        layout.addWidget(heatmap_box)

        resistance_box = QGroupBox("Паттерн резистентности")
        resistance_layout = QVBoxLayout(resistance_box)
        self._resistance_grid = ResistanceGrid()
        self._resistance_grid.setMinimumHeight(220)
        resistance_layout.addWidget(self._resistance_grid)
        layout.addWidget(resistance_box)
        layout.addStretch()

    def _material_type_ids(self) -> dict[str, int]:
        try:
            rows = self.controller.reference_service.list_material_types()
        except Exception:
            return {}
        result: dict[str, int] = {}
        for row in rows:
            row_id = getattr(row, "id", None)
            if not isinstance(row_id, int):
                continue
            for attr in ("name", "code"):
                value = getattr(row, attr, None)
                if isinstance(value, str) and value:
                    result[value.lower()] = row_id
        return result

    def _on_heatmap_cell_clicked(self, dept: str, micro: str) -> None:
        _ = (dept, micro)
