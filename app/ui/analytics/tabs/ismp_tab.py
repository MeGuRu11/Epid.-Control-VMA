from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.table_utils import resize_columns_to_content, set_table_read_only

if TYPE_CHECKING:
    from app.application.dto.analytics_dto import AnalyticsSearchRequest
    from app.ui.analytics.controller import AnalyticsController


class IsmpTab(QWidget):
    def __init__(self, controller: AnalyticsController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def refresh(self, request: AnalyticsSearchRequest) -> None:
        data = self.controller.get_ismp_metrics(request)
        self._apply_ismp_metrics(data)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        ismp_box = QGroupBox("ИСМП показатели")
        ismp_layout = QVBoxLayout(ismp_box)
        ismp_row = QHBoxLayout()
        self.ismp_total_cases = QLabel("Госпитализаций: 0")
        self.ismp_total_cases.setObjectName("chipLabel")
        self.ismp_cases = QLabel("Случаев ИСМП: 0")
        self.ismp_cases.setObjectName("chipLabel")
        self.ismp_incidence = QLabel("Инцидентность: 0.0 на 1000")
        self.ismp_incidence.setObjectName("chipLabel")
        self.ismp_density = QLabel("Плотность: 0.0 на 1000 койко-дн.")
        self.ismp_density.setObjectName("chipLabel")
        self.ismp_prevalence = QLabel("Превалентность: 0.0%")
        self.ismp_prevalence.setObjectName("chipLabel")
        for chip in (
            self.ismp_total_cases,
            self.ismp_cases,
            self.ismp_incidence,
            self.ismp_density,
            self.ismp_prevalence,
        ):
            ismp_row.addWidget(chip)
        ismp_row.addStretch()
        ismp_layout.addLayout(ismp_row)

        self.ismp_table = QTableWidget(0, 2)
        self.ismp_table.setHorizontalHeaderLabels(["Тип ИСМП", "Количество"])
        self.ismp_table.horizontalHeader().setStretchLastSection(True)
        self.ismp_table.verticalHeader().setVisible(False)
        self.ismp_table.setAlternatingRowColors(True)
        self.ismp_table.setMinimumHeight(160)
        set_table_read_only(self.ismp_table)
        ismp_layout.addWidget(self.ismp_table)
        layout.addWidget(ismp_box)
        layout.addStretch()

    def _apply_ismp_metrics(self, data: dict[str, Any]) -> None:
        self.ismp_total_cases.setText(f"Госпитализаций: {int(data.get('total_cases', 0))}")
        self.ismp_cases.setText(f"Случаев ИСМП: {int(data.get('ismp_cases', 0))}")
        self.ismp_incidence.setText(f"Инцидентность: {float(data.get('incidence', 0.0)):.1f} на 1000")
        self.ismp_density.setText(f"Плотность: {float(data.get('density', 0.0)):.1f} на 1000 койко-дн.")
        self.ismp_prevalence.setText(f"Превалентность: {float(data.get('prevalence', 0.0)):.1f}%")

        by_type = cast(dict[str, int], data.get("by_type") or {})
        self.ismp_table.clearContents()
        self.ismp_table.setRowCount(len(by_type))
        for row_index, (name, count) in enumerate(by_type.items()):
            self.ismp_table.setItem(row_index, 0, QTableWidgetItem(str(name)))
            self.ismp_table.setItem(row_index, 1, QTableWidgetItem(str(count)))
        resize_columns_to_content(self.ismp_table)
