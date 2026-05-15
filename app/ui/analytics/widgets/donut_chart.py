from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPaintEvent, QPalette
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

DONUT_COLORS = [
    "#6FB9AD",
    "#F59E0B",
    "#EF4444",
    "#8B5CF6",
    "#10B981",
    "#F97316",
    "#3B82F6",
]


class DonutSegment(QWidget):
    """Цветной индикатор и подпись легенды."""

    def __init__(self, label: str, color: str, value: int, total: int) -> None:
        super().__init__()
        self.setObjectName("donutSegment")
        dot = QLabel("●")
        dot.setObjectName("donutLegendDot")
        dot.setPalette(self._dot_palette(color))
        pct = f"{value / total * 100:.1f}%" if total else "0%"
        text = QLabel(f"{label}: {value} ({pct})")
        text.setObjectName("donutLegendText")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(6)
        row.addWidget(dot)
        row.addWidget(text)
        row.addStretch()

    def _dot_palette(self, color: str) -> QPalette:
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(color))
        return palette


class DonutCanvas(QWidget):
    """Кольцевая диаграмма без осей и подписей."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data: list[tuple[str, int, str]] = []
        self.setMinimumSize(180, 180)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_data(self, data: list[tuple[str, int, str]]) -> None:
        self._data = data
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        _ = event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        total = sum(value for _label, value, _color in self._data)
        if total <= 0:
            return

        width = self.width()
        height = self.height()
        size = min(width, height) - 10
        x = (width - size) / 2
        y = (height - size) / 2
        start_angle = -90.0
        hole_ratio = 0.55

        for _label, value, color in self._data:
            span = value / total * 360
            outer = QPainterPath()
            outer.moveTo(width / 2, height / 2)
            outer.arcTo(x, y, size, size, start_angle, span)
            outer.closeSubpath()

            inner_size = size * hole_ratio
            inner_x = x + (size - inner_size) / 2
            inner_y = y + (size - inner_size) / 2
            inner = QPainterPath()
            inner.addEllipse(inner_x, inner_y, inner_size, inner_size)

            painter.fillPath(outer.subtracted(inner), QColor(color))
            start_angle += span


class DonutChart(QWidget):
    """DonutCanvas с легендой справа."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._canvas = DonutCanvas()
        self._legend = QVBoxLayout()
        self._legend.setContentsMargins(0, 0, 0, 0)
        self._legend.setSpacing(4)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        root.addWidget(self._canvas)
        root.addLayout(self._legend)
        root.addStretch()

    def set_data(self, items: list[tuple[str, int]]) -> None:
        total = sum(value for _label, value in items)
        colored = [
            (label, value, DONUT_COLORS[index % len(DONUT_COLORS)])
            for index, (label, value) in enumerate(items)
        ]
        self._canvas.set_data(colored)

        while self._legend.count():
            item = self._legend.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for label, value, color in colored:
            self._legend.addWidget(DonutSegment(label, color, value, total))
        self._legend.addStretch()


class IsmpDepartmentBar(QWidget):
    """Горизонтальные бары топ-N отделений по числу ИСМП."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)

    def set_data(self, items: list[tuple[str, int]], max_n: int = 8) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not items:
            return

        data = items[:max_n]
        max_value = max(value for _dept, value in data) or 1
        for dept, count in data:
            self._layout.addWidget(self._row(dept, count, max_value))

    def _row(self, dept: str, count: int, max_value: int) -> QWidget:
        container = QWidget()
        container.setObjectName("ismpDeptBarRow")
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        label = QLabel(self._short_label(dept, 22))
        label.setObjectName("ismpDeptName")
        label.setFixedWidth(180)
        label.setToolTip(dept)

        bar = QProgressBar()
        bar.setObjectName("ismpDeptBar")
        bar.setRange(0, max_value)
        bar.setValue(count)
        bar.setTextVisible(False)
        bar.setFixedHeight(16)

        count_label = QLabel(str(count))
        count_label.setObjectName("ismpDeptCount")
        count_label.setFixedWidth(30)
        count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        row.addWidget(label)
        row.addWidget(bar, 1)
        row.addWidget(count_label)
        return container

    def _short_label(self, value: str, limit: int) -> str:
        return value if len(value) <= limit else f"{value[: limit - 1]}…"
