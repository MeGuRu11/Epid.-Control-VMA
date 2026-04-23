from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any, cast

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    import pyqtgraph as pg
except Exception:  # pragma: no cover
    pg = None

TOP_MICROBES_LEFT_LABEL = "\u0414\u043e\u043b\u044f \u0432\u044b\u0434\u0435\u043b\u0435\u043d\u0438\u0439, %"
TOP_MICROBES_BOTTOM_LABEL = "\u041c\u0438\u043a\u0440\u043e\u043e\u0440\u0433\u0430\u043d\u0438\u0437\u043c\u044b"
TREND_LEFT_LABEL = "\u0414\u043e\u043b\u044f \u043f\u043e\u043b\u043e\u0436\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0445, %"
TREND_BOTTOM_LABEL = "\u0414\u0430\u0442\u0430"
_CHART_FALLBACK_TEXT = "\u0413\u0440\u0430\u0444\u0438\u043a \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d \u0432 \u0442\u0435\u043a\u0443\u0449\u0435\u0439 \u0441\u0431\u043e\u0440\u043a\u0435"
_PYQTGRAPH_MISSING_TEXT = "pyqtgraph \u043d\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d"
logger = logging.getLogger(__name__)


class TopMicrobesChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._plot: Any = None
        self._items: list[tuple[str, float]] = []
        self._fallback: QLabel | None = None
        if pg is None:
            self._show_fallback(_PYQTGRAPH_MISSING_TEXT)
            return
        try:
            self._plot = pg.PlotWidget()
            self._plot.setBackground("w")
            self._plot.showGrid(x=True, y=True, alpha=0.2)
            self._plot.setLabel("left", TOP_MICROBES_LEFT_LABEL)
            self._plot.setLabel("bottom", TOP_MICROBES_BOTTOM_LABEL)
            self._lock_plot_interaction()
            self._layout.addWidget(cast(QWidget, self._plot))
        except Exception:  # noqa: BLE001
            logger.exception("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0438\u043d\u0438\u0446\u0438\u0430\u043b\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u0442\u044c TopMicrobesChart")
            self._plot = None
            self._show_fallback(_CHART_FALLBACK_TEXT)

    def update_data(self, items: Iterable[tuple[str, float]]) -> None:
        self._items = list(items)
        if self._plot is None or pg is None:
            return
        try:
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
        except Exception:  # noqa: BLE001
            logger.exception("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c TopMicrobesChart")

    def _lock_plot_interaction(self) -> None:
        if self._plot is None:
            return
        self._plot.setMouseEnabled(x=False, y=False)
        view = self._plot.getViewBox()
        view.setMouseEnabled(x=False, y=False)
        view.setMenuEnabled(False)

    def _show_fallback(self, text: str) -> None:
        if self._fallback is None:
            self._fallback = QLabel(text)
            self._layout.addWidget(self._fallback)
            return
        self._fallback.setText(text)


class TrendChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._plot: Any = None
        self._items: list[tuple[str, float]] = []
        self._fallback: QLabel | None = None
        if pg is None:
            self._show_fallback(_PYQTGRAPH_MISSING_TEXT)
            return
        try:
            self._plot = pg.PlotWidget()
            self._plot.setBackground("w")
            self._plot.showGrid(x=True, y=True, alpha=0.2)
            self._plot.setLabel("left", TREND_LEFT_LABEL)
            self._plot.setLabel("bottom", TREND_BOTTOM_LABEL)
            self._lock_plot_interaction()
            self._layout.addWidget(cast(QWidget, self._plot))
        except Exception:  # noqa: BLE001
            logger.exception("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0438\u043d\u0438\u0446\u0438\u0430\u043b\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u0442\u044c TrendChart")
            self._plot = None
            self._show_fallback(_CHART_FALLBACK_TEXT)

    def update_data(self, items: Iterable[tuple[str, float]]) -> None:
        self._items = list(items)
        if self._plot is None or pg is None:
            return
        try:
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
        except Exception:  # noqa: BLE001
            logger.exception("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c TrendChart")

    def _lock_plot_interaction(self) -> None:
        if self._plot is None:
            return
        self._plot.setMouseEnabled(x=False, y=False)
        view = self._plot.getViewBox()
        view.setMouseEnabled(x=False, y=False)
        view.setMenuEnabled(False)

    def _show_fallback(self, text: str) -> None:
        if self._fallback is None:
            self._fallback = QLabel(text)
            self._layout.addWidget(self._fallback)
            return
        self._fallback.setText(text)
