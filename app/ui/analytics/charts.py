from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    import pyqtgraph as pg
except Exception:  # pragma: no cover
    pg = None

TOP_MICROBES_LEFT_LABEL = "Доля выделений, %"
TOP_MICROBES_BOTTOM_LABEL = "Микроорганизмы"
TREND_LEFT_LABEL = "Доля положительных, %"
TREND_BOTTOM_LABEL = "Дата"


class TopMicrobesChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self._plot: Any = None
        self._items: list[tuple[str, float]] = []
        if pg is None:
            self._fallback = QLabel("pyqtgraph не установлен")
            layout.addWidget(self._fallback)
            return
        self._plot = pg.PlotWidget()
        self._plot.setBackground("w")
        self._plot.showGrid(x=True, y=True, alpha=0.2)
        self._plot.setLabel("left", TOP_MICROBES_LEFT_LABEL)
        self._plot.setLabel("bottom", TOP_MICROBES_BOTTOM_LABEL)
        self._lock_plot_interaction()
        layout.addWidget(cast(QWidget, self._plot))

    def update_data(self, items: Iterable[tuple[str, float]]) -> None:
        self._items = list(items)
        if self._plot is None or pg is None:
            return
        labels = [name for name, _count in self._items]
        values = [count for _name, count in self._items]
        self._plot.clear()
        self._plot.setYRange(0, 100, padding=0.02)
        ax = self._plot.getAxis("bottom")
        if not values:
            ax.setTicks([[]])
            self._plot.setXRange(-0.5, 0.5, padding=0.02)
            return
        x = list(range(len(values)))
        bar = pg.BarGraphItem(x=x, height=values, width=0.6, brush="#4C78A8")
        self._plot.addItem(bar)
        ax.setTicks([list(zip(x, labels, strict=False))])
        self._plot.setXRange(-0.5, max(len(values) - 0.5, 0.5), padding=0.02)

    def _lock_plot_interaction(self) -> None:
        if self._plot is None:
            return
        self._plot.setMouseEnabled(x=False, y=False)
        view = self._plot.getViewBox()
        view.setMouseEnabled(x=False, y=False)
        view.setMenuEnabled(False)


class TrendChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self._plot: Any = None
        self._items: list[tuple[str, float]] = []
        if pg is None:
            self._fallback = QLabel("pyqtgraph не установлен")
            layout.addWidget(self._fallback)
            return
        self._plot = pg.PlotWidget()
        self._plot.setBackground("w")
        self._plot.showGrid(x=True, y=True, alpha=0.2)
        self._plot.setLabel("left", TREND_LEFT_LABEL)
        self._plot.setLabel("bottom", TREND_BOTTOM_LABEL)
        self._lock_plot_interaction()
        layout.addWidget(cast(QWidget, self._plot))

    def update_data(self, items: Iterable[tuple[str, float]]) -> None:
        self._items = list(items)
        if self._plot is None or pg is None:
            return
        labels = [label for label, _value in self._items]
        values = [value for _label, value in self._items]
        self._plot.clear()
        self._plot.setYRange(0, 100, padding=0.02)
        ax = self._plot.getAxis("bottom")
        if not values:
            ax.setTicks([[]])
            self._plot.setXRange(-0.5, 0.5, padding=0.02)
            return
        x = list(range(len(values)))
        bar = pg.BarGraphItem(x=x, height=values, width=0.75, brush="#4C78A8")
        self._plot.addItem(bar)
        ax.setTicks([list(zip(x, labels, strict=False))])
        self._plot.setXRange(-0.5, max(len(values) - 0.5, 0.5), padding=0.02)

    def _lock_plot_interaction(self) -> None:
        if self._plot is None:
            return
        self._plot.setMouseEnabled(x=False, y=False)
        view = self._plot.getViewBox()
        view.setMouseEnabled(x=False, y=False)
        view.setMenuEnabled(False)
