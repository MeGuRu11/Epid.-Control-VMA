from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget


class Sparkline(QWidget):
    """Мини-график тренда для KPI-карточек без осей и меток."""

    DEFAULT_COLOR = QColor("#6FB9AD")
    EMPTY_COLOR = QColor("#D0CEC8")

    def __init__(
        self,
        parent: QWidget | None = None,
        color: QColor | None = None,
    ) -> None:
        super().__init__(parent)
        self._values: list[float] = []
        self._color = color or self.DEFAULT_COLOR
        self.setFixedSize(70, 28)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_data(self, values: list[float | int]) -> None:
        """Передать значения для мини-графика."""
        self._values = [float(value) for value in values]
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(70, 28)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        _ = event
        if len(self._values) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        padding = 3
        minimum = min(self._values)
        maximum = max(self._values)
        spread = maximum - minimum or 1.0

        def _x(index: int) -> float:
            return padding + index * (width - 2 * padding) / (len(self._values) - 1)

        def _y(value: float) -> float:
            return height - padding - (value - minimum) / spread * (height - 2 * padding)

        path = QPainterPath()
        path.moveTo(_x(0), _y(self._values[0]))
        for index, value in enumerate(self._values[1:], 1):
            path.lineTo(_x(index), _y(value))

        pen = QPen(self._color, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)
