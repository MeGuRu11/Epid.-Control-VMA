from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.analytics.chart_data import TimeGrouping, coerce_time_grouping
from app.ui.analytics.charts import TopMicrobesChart, TrendChart
from app.ui.analytics.view_utils import build_top_microbe_chart_items, build_trend_chart_items
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.table_utils import (
    connect_combo_autowidth,
    resize_columns_to_content,
    set_table_read_only,
)

if TYPE_CHECKING:
    from app.application.dto.analytics_dto import AnalyticsSearchRequest
    from app.ui.analytics.controller import AnalyticsController


class OverviewTab(QWidget):
    def __init__(self, controller: AnalyticsController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._last_request: AnalyticsSearchRequest | None = None
        self._build_ui()

    def refresh(self, request: AnalyticsSearchRequest) -> None:
        self._last_request = request
        self.controller.clear_cache()
        agg = self.controller.get_aggregates(request)
        self._apply_aggregate_summary(agg)
        self._apply_department_summary(self.controller.get_department_summary(request))
        self._apply_trend(self.controller.get_trend(request), request)
        self._apply_compare(self.controller.compare_periods(request, self._compare_days()))

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self._build_summary_row(layout)
        layout.addWidget(self._build_dashboard_box())
        layout.addWidget(self._build_top_box())
        layout.addStretch()

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

    def _build_dashboard_box(self) -> QGroupBox:
        box = QGroupBox("Сводка")
        dashboard_layout = QVBoxLayout(box)
        controls = QHBoxLayout()
        self.compare_period = QComboBox()
        self.compare_period.addItem("Неделя", 7)
        self.compare_period.addItem("Месяц", 30)
        connect_combo_autowidth(self.compare_period)
        self.time_grouping = QComboBox()
        self.time_grouping.addItem("Авто", TimeGrouping.AUTO.value)
        self.time_grouping.addItem("Дни", TimeGrouping.DAY.value)
        self.time_grouping.addItem("Недели", TimeGrouping.WEEK.value)
        self.time_grouping.addItem("Месяцы", TimeGrouping.MONTH.value)
        connect_combo_autowidth(self.time_grouping)
        self.time_grouping.currentIndexChanged.connect(lambda _index: self._refresh_last())
        self.compare_label = QLabel("Сравнение: -")
        self.compare_label.setObjectName("chipLabel")
        refresh_btn = QPushButton("Обновить сводку")
        compact_button(refresh_btn)
        refresh_btn.clicked.connect(self._refresh_last)
        controls.addWidget(QLabel("Период сравнения"))
        controls.addWidget(self.compare_period)
        controls.addWidget(QLabel("Группировка"))
        controls.addWidget(self.time_grouping)
        controls.addWidget(self.compare_label)
        controls.addStretch()
        controls.addWidget(refresh_btn)
        dashboard_layout.addLayout(controls)

        self.department_table = QTableWidget(0, 5)
        self.department_table.setHorizontalHeaderLabels(
            ["Отделение", "Проб", "Положительных", "Доля", "Последняя дата"]
        )
        self.department_table.horizontalHeader().setStretchLastSection(True)
        self.department_table.verticalHeader().setVisible(False)
        self.department_table.setAlternatingRowColors(True)
        self.department_table.setMinimumHeight(240)
        set_table_read_only(self.department_table)
        dashboard_layout.addWidget(self.department_table)

        dashboard_layout.addWidget(QLabel("Тренд по периодам"))
        self.trend_chart = TrendChart()
        self.trend_chart.setMinimumHeight(340)
        dashboard_layout.addWidget(self.trend_chart)
        return box

    def _build_top_box(self) -> QGroupBox:
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
        return top_box

    def _refresh_last(self) -> None:
        if self._last_request is not None:
            self.refresh(self._last_request)

    def _compare_days(self) -> int:
        return int(self.compare_period.currentData() or 7)

    def _selected_time_grouping(self) -> TimeGrouping:
        return coerce_time_grouping(self.time_grouping.currentData())

    def _apply_aggregate_summary(self, agg: dict[str, Any]) -> None:
        total = int(agg.get("total", 0))
        positives = int(agg.get("positives", 0))
        positive_share = float(agg.get("positive_share", 0.0))
        top_microbes = cast(list[tuple[str, int]], agg.get("top_microbes", []))
        total_microbe_isolations = int(
            agg.get("total_microbe_isolations") or sum(count for _name, count in top_microbes)
        )
        chart_items = build_top_microbe_chart_items(
            top_microbes,
            total_microbe_isolations=total_microbe_isolations,
        )
        self.summary_total.setText(f"Итого: {total}")
        self.summary_positive.setText(f"Положительных: {positives}")
        self.summary_share.setText(f"Доля: {positive_share * 100:.1f}%")
        self.chart.update_data(chart_items)
        self._apply_top_table(top_microbes, chart_items)

    def _apply_top_table(self, top_microbes: list[tuple[str, int]], chart_items: list[tuple[str, float]]) -> None:
        self.top_table.clearContents()
        self.top_table.setRowCount(len(top_microbes))
        for idx, (name, count) in enumerate(top_microbes):
            self.top_table.setItem(idx, 0, QTableWidgetItem(name))
            self.top_table.setItem(idx, 1, QTableWidgetItem(str(count)))
            share = chart_items[idx][1] if idx < len(chart_items) else 0.0
            self.top_table.setItem(idx, 2, QTableWidgetItem(f"{share:.1f}%"))
        resize_columns_to_content(self.top_table)

    def _apply_department_summary(self, rows: list[dict[str, Any]]) -> None:
        self.department_table.clearContents()
        self.department_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            total = int(row.get("total", 0))
            positives = int(row.get("positives", 0))
            share = float(row.get("positive_share", 0.0)) * 100
            values = [
                str(row.get("department_name") or row.get("department") or ""),
                str(total),
                str(positives),
                f"{share:.1f}%",
                str(row.get("last_date") or row.get("latest_date") or ""),
            ]
            for column, value in enumerate(values):
                self.department_table.setItem(row_index, column, QTableWidgetItem(value))
        resize_columns_to_content(self.department_table)

    def _apply_trend(self, rows: list[dict[str, Any]], request: AnalyticsSearchRequest) -> None:
        chart_items = build_trend_chart_items(
            rows,
            date_from=request.date_from,
            date_to=request.date_to,
            grouping=self._selected_time_grouping(),
        )
        self.trend_chart.update_data(chart_items)

    def _apply_compare(self, compare: dict[str, Any] | None) -> None:
        if not compare:
            self.compare_label.setText("Сравнение: -")
            return
        current = cast(dict[str, Any], compare.get("current") or {})
        previous = cast(dict[str, Any], compare.get("previous") or {})
        current_total = int(current.get("total", 0))
        previous_total = int(previous.get("total", 0))
        delta = current_total - previous_total
        self.compare_label.setText(f"Сравнение: {current_total} / {previous_total} ({delta:+d})")
