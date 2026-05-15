from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget


class HeatmapCell(QLabel):
    clicked = Signal(str, str)

    def __init__(self, dept: str, micro: str, value: int, max_value: int) -> None:
        super().__init__(str(value) if value else "")
        self._dept = dept
        self._micro = micro
        self.setObjectName("heatmapCell")
        self.setProperty("tone", self._tone(value, max_value))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(60, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{dept}: {micro} — {value}")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        super().mousePressEvent(event)
        self.clicked.emit(self._dept, self._micro)

    def _tone(self, value: int, max_value: int) -> str:
        if max_value <= 0 or value <= 0:
            return "empty"
        ratio = value / max_value
        if ratio < 0.33:
            return "low"
        if ratio < 0.66:
            return "medium"
        return "high"


class Heatmap(QWidget):
    """Матрица «Отделения × Микроорганизмы»."""

    cell_clicked = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._grid_widget = QWidget()
        self._grid_widget.setObjectName("heatmapGrid")
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(2)

        scroll = QScrollArea()
        scroll.setObjectName("heatmapScrollArea")
        scroll.setWidget(self._grid_widget)
        scroll.setWidgetResizable(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def set_data(
        self,
        matrix: dict[str, dict[str, int]],
        ordered_micros: list[str],
    ) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not matrix or not ordered_micros:
            return

        depts = list(matrix.keys())
        max_value = max((matrix[dept].get(micro, 0) for dept in depts for micro in ordered_micros), default=1)

        for column, micro in enumerate(ordered_micros, start=1):
            label = QLabel(self._short_label(micro, 12))
            label.setObjectName("heatmapHeaderLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setToolTip(micro)
            self._grid.addWidget(label, 0, column)

        for row, dept in enumerate(depts, start=1):
            dept_label = QLabel(self._short_label(dept, 18))
            dept_label.setObjectName("heatmapDeptLabel")
            dept_label.setToolTip(dept)
            self._grid.addWidget(dept_label, row, 0)
            for column, micro in enumerate(ordered_micros, start=1):
                value = matrix[dept].get(micro, 0)
                cell = HeatmapCell(dept, micro, value, max_value)
                cell.clicked.connect(self.cell_clicked.emit)
                self._grid.addWidget(cell, row, column)

    def _short_label(self, value: str, limit: int) -> str:
        tail = value.split(" - ")[-1]
        return tail if len(tail) <= limit else f"{tail[: limit - 1]}…"
