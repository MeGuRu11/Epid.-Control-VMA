from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.ui.theme import theme_qcolor


class PatternOverlay(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._dot_color = theme_qcolor("text", alpha=18)
        self._dot_step = 40
        self._dot_radius = 1

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(self._dot_color)
        pen.setWidth(1)
        painter.setPen(pen)
        width = self.width()
        height = self.height()
        step = self._dot_step
        radius = self._dot_radius
        for x in range(0, width, step):
            for y in range(0, height, step):
                painter.drawEllipse(x, y, radius, radius)

