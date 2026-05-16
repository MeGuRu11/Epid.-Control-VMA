from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
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
from app.ui.analytics.tabs import TAB_ISMP, TAB_MICROBIOLOGY
from app.ui.analytics.view_utils import (
    build_top_microbe_chart_items,
    build_trend_chart_items,
    make_section_frame,
)
from app.ui.analytics.widgets.empty_state import CurrentWidgetStack, make_inline_placeholder
from app.ui.analytics.widgets.kpi_card import KpiCard
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
    drill_down_requested = Signal(int)

    def __init__(self, controller: AnalyticsController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._last_request: AnalyticsSearchRequest | None = None
        self._kpi_hosp = KpiCard("Госпитализаций", "Г", "neutral", "neutral", show_sparkline=True)
        self._kpi_ismp = KpiCard("Случаев ИСМП", "И", "negative", "negative", show_sparkline=False)
        self._kpi_pos = KpiCard("Положительных", "Л", "lab", "neutral", show_sparkline=True)
        self._kpi_prev = KpiCard("Превалентность", "%", "calc", "negative", show_sparkline=False)
        self._kpi_ismp.clicked.connect(lambda: self.drill_down_requested.emit(TAB_ISMP))
        self._kpi_pos.clicked.connect(lambda: self.drill_down_requested.emit(TAB_MICROBIOLOGY))
        self._kpi_prev.clicked.connect(lambda: self.drill_down_requested.emit(TAB_ISMP))
        self._build_ui()

    def refresh(self, request: AnalyticsSearchRequest) -> None:
        self._last_request = request
        self.controller.clear_cache()
        agg = self.controller.get_aggregates(request)
        ismp = self.controller.get_ismp_metrics(request)
        compare = self.controller.compare_periods(request, self._compare_days())
        trend_rows = self.controller.get_trend(request)
        self._update_kpi(agg, ismp, compare, trend_rows=trend_rows)
        self._apply_aggregate_summary(agg)
        self._apply_department_summary(self.controller.get_department_summary(request))
        self._apply_trend(trend_rows, request)
        self._apply_compare(compare)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self._content_widget = QWidget()
        content_layout = QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(12)
        for column, card in enumerate((self._kpi_hosp, self._kpi_ismp, self._kpi_pos, self._kpi_prev)):
            kpi_grid.addWidget(card, 0, column)
            kpi_grid.setColumnStretch(column, 1)
        content_layout.addLayout(kpi_grid)
        self._build_summary_row(content_layout)
        content_layout.addWidget(self._build_dashboard_box())
        content_layout.addWidget(self._build_top_box())
        layout.addWidget(self._content_widget)
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

    def _build_dashboard_box(self) -> QWidget:
        box, dashboard_layout = make_section_frame("Сводка")
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
        self._department_stack = CurrentWidgetStack()
        self._department_stack.addWidget(self.department_table)
        self._department_empty = make_inline_placeholder("Нет данных за выбранный период")
        self._department_stack.addWidget(self._department_empty)
        self._department_stack.setCurrentWidget(self._department_empty)
        dashboard_layout.addWidget(self._department_stack)

        dashboard_layout.addWidget(QLabel("Тренд по периодам"))
        self._trend_stack = CurrentWidgetStack()
        self.trend_chart = TrendChart()
        self.trend_chart.setMinimumHeight(340)
        self._trend_stack.addWidget(self.trend_chart)
        self._trend_empty = make_inline_placeholder("Нет данных за выбранный период")
        self._trend_stack.addWidget(self._trend_empty)
        self._trend_stack.setCurrentWidget(self._trend_empty)
        dashboard_layout.addWidget(self._trend_stack)
        return box

    def _build_top_box(self) -> QWidget:
        top_box, top_layout = make_section_frame("Топ микроорганизмов")
        self._top_chart_stack = CurrentWidgetStack()
        self.chart = TopMicrobesChart()
        self.chart.setMinimumHeight(340)
        self._top_chart_stack.addWidget(self.chart)
        self._top_chart_empty = make_inline_placeholder("Нет данных за выбранный период")
        self._top_chart_stack.addWidget(self._top_chart_empty)
        self._top_chart_stack.setCurrentWidget(self._top_chart_empty)
        top_layout.addWidget(self._top_chart_stack)
        self.top_table = QTableWidget(0, 3)
        self.top_table.setHorizontalHeaderLabels(["Микроорганизм", "Количество", "Доля"])
        self.top_table.horizontalHeader().setStretchLastSection(True)
        self.top_table.verticalHeader().setVisible(False)
        self.top_table.setAlternatingRowColors(True)
        self.top_table.setMinimumHeight(220)
        set_table_read_only(self.top_table)
        self._top_table_stack = CurrentWidgetStack()
        self._top_table_stack.addWidget(self.top_table)
        self._top_table_empty = make_inline_placeholder("Нет данных за выбранный период")
        self._top_table_stack.addWidget(self._top_table_empty)
        self._top_table_stack.setCurrentWidget(self._top_table_empty)
        top_layout.addWidget(self._top_table_stack)
        return top_box

    def _refresh_last(self) -> None:
        if self._last_request is not None:
            self.refresh(self._last_request)

    def _compare_days(self) -> int:
        return int(self.compare_period.currentData() or 7)

    def _selected_time_grouping(self) -> TimeGrouping:
        return coerce_time_grouping(self.time_grouping.currentData())

    def _set_stack_content(
        self,
        stack: CurrentWidgetStack,
        content: object,
        empty: QWidget,
        has_data: bool,
    ) -> None:
        if has_data and isinstance(content, QWidget) and stack.indexOf(content) >= 0:
            stack.setCurrentWidget(content)
        else:
            stack.setCurrentWidget(empty)

    def _update_kpi(
        self,
        agg: dict[str, Any],
        ismp: dict[str, Any],
        compare: dict[str, Any] | None,
        trend_rows: list[dict[str, Any]] | None = None,
    ) -> None:
        from app.application.reporting.formatters import format_percent

        previous = cast(dict[str, Any], compare.get("previous", {}) if compare else {})

        total_cur = int(ismp.get("total_cases", 0))
        self._kpi_hosp.set_value(str(total_cur))
        self._kpi_hosp.set_trend(total_cur, self._numeric_or_none(previous.get("total")))

        self._kpi_ismp.set_value(str(int(ismp.get("ismp_cases", 0))))
        self._kpi_ismp.clear_trend()

        pos_cur = int(agg.get("positives", 0))
        share = float(agg.get("positive_share", 0.0))
        self._kpi_pos.set_value(f"{pos_cur} ({format_percent(share)})")
        self._kpi_pos.set_trend(pos_cur, self._numeric_or_none(previous.get("positives")))

        prevalence = float(ismp.get("prevalence", 0.0))
        self._kpi_prev.set_value(format_percent(prevalence / 100))
        self._kpi_prev.clear_trend()

        if trend_rows:
            self._kpi_hosp.set_sparkline_data([self._number_from_row(row.get("total")) for row in trend_rows])
            self._kpi_pos.set_sparkline_data([self._number_from_row(row.get("positives")) for row in trend_rows])
        else:
            self._kpi_hosp.set_sparkline_data([])
            self._kpi_pos.set_sparkline_data([])

    def _numeric_or_none(self, value: object) -> float | int | None:
        if isinstance(value, int | float):
            return value
        return None

    def _number_from_row(self, value: object) -> float | int:
        if isinstance(value, int | float):
            return value
        return 0

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
        self._set_stack_content(self._top_chart_stack, self.chart, self._top_chart_empty, bool(top_microbes))
        self._apply_top_table(top_microbes, chart_items)

    def _apply_top_table(self, top_microbes: list[tuple[str, int]], chart_items: list[tuple[str, float]]) -> None:
        self.top_table.clearContents()
        self.top_table.setRowCount(len(top_microbes))
        self._top_table_stack.setCurrentWidget(self.top_table if top_microbes else self._top_table_empty)
        for idx, (name, count) in enumerate(top_microbes):
            self.top_table.setItem(idx, 0, QTableWidgetItem(name))
            self.top_table.setItem(idx, 1, QTableWidgetItem(str(count)))
            share = chart_items[idx][1] if idx < len(chart_items) else 0.0
            self.top_table.setItem(idx, 2, QTableWidgetItem(f"{share:.1f}%"))
        resize_columns_to_content(self.top_table)

    def _apply_department_summary(self, rows: list[dict[str, Any]]) -> None:
        self.department_table.clearContents()
        self.department_table.setRowCount(len(rows))
        self._department_stack.setCurrentWidget(self.department_table if rows else self._department_empty)
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
        self._set_stack_content(self._trend_stack, self.trend_chart, self._trend_empty, bool(rows))

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
