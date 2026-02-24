from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    import pyqtgraph as pg
except Exception:  # pragma: no cover
    pg = None


class TopMicrobesChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        if pg is None:
            self._fallback = QLabel("pyqtgraph не установлен")
            layout.addWidget(self._fallback)
            self._plot = None
            return
        self._plot = pg.PlotWidget()
        self._plot.setBackground("w")
        self._plot.showGrid(x=True, y=True, alpha=0.2)
        self._plot.setLabel("left", "Количество")
        self._plot.setLabel("bottom", "Микроорганизмы")
        self._lock_plot_interaction()
        layout.addWidget(self._plot)

    def update_data(self, items: Iterable[tuple[str, int]]) -> None:
        if self._plot is None:
            return
        labels = [name for name, _count in items]
        values = [count for _name, count in items]
        self._plot.clear()
        if not values:
            return
        x = list(range(len(values)))
        bar = pg.BarGraphItem(x=x, height=values, width=0.6, brush="#4C78A8")
        self._plot.addItem(bar)
        ax = self._plot.getAxis("bottom")
        ax.setTicks([list(zip(x, labels, strict=False))])
        self._plot.setYRange(0, max(values) * 1.1)

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
        if pg is None:
            self._fallback = QLabel("pyqtgraph не установлен")
            layout.addWidget(self._fallback)
            self._plot = None
            return
        self._plot = pg.PlotWidget()
        self._plot.setBackground("w")
        self._plot.showGrid(x=True, y=True, alpha=0.2)
        self._plot.setLabel("left", "Количество")
        self._plot.setLabel("bottom", "Дата")
        self._lock_plot_interaction()
        layout.addWidget(self._plot)

    def update_data(self, items: Iterable[tuple[str, int, int]]) -> None:
        if self._plot is None:
            return
        labels = [label for label, _total, _pos in items]
        totals = [total for _label, total, _pos in items]
        positives = [pos for _label, _total, pos in items]
        self._plot.clear()
        if not totals:
            return
        x = list(range(len(totals)))
        total_line = pg.PlotDataItem(x=x, y=totals, pen=pg.mkPen("#4C78A8", width=2))
        pos_line = pg.PlotDataItem(x=x, y=positives, pen=pg.mkPen("#E18A85", width=2))
        self._plot.addItem(total_line)
        self._plot.addItem(pos_line)
        ax = self._plot.getAxis("bottom")
        ax.setTicks([list(zip(x, labels, strict=False))])
        max_val = max(totals + positives)
        self._plot.setYRange(0, max_val * 1.1)

    def _lock_plot_interaction(self) -> None:
        if self._plot is None:
            return
        self._plot.setMouseEnabled(x=False, y=False)
        view = self._plot.getViewBox()
        view.setMouseEnabled(x=False, y=False)
        view.setMenuEnabled(False)
