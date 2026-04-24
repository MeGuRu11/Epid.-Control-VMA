from __future__ import annotations

from typing import Any

import pytest
from PySide6.QtWidgets import QLabel, QWidget

from app.ui.analytics import charts


class _FakeAxis:
    def __init__(self) -> None:
        self.ticks: list[list[object]] = []

    def setTicks(self, ticks: list[list[object]]) -> None:  # noqa: N802
        self.ticks = ticks


class _FakeViewBox:
    def setMouseEnabled(self, *, x: bool, y: bool) -> None:  # noqa: N802
        _ = (x, y)

    def setMenuEnabled(self, enabled: bool) -> None:  # noqa: N802
        _ = enabled


class _FakePlotWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.axis = _FakeAxis()

    def setBackground(self, _value: str) -> None:  # noqa: N802
        return None

    def showGrid(self, *, x: bool, y: bool, alpha: float) -> None:  # noqa: N802
        _ = (x, y, alpha)

    def setLabel(self, _axis: str, _text: str) -> None:  # noqa: N802
        return None

    def clear(self) -> None:
        return None

    def setYRange(self, _min_value: int, _max_value: int, *, padding: float) -> None:  # noqa: N802
        _ = padding

    def getAxis(self, _axis: str) -> _FakeAxis:  # noqa: N802
        return self.axis

    def setXRange(self, _min_value: float, _max_value: float, *, padding: float) -> None:  # noqa: N802
        _ = padding

    def addItem(self, _item: object) -> None:  # noqa: N802
        return None

    def setMouseEnabled(self, *, x: bool, y: bool) -> None:  # noqa: N802
        _ = (x, y)

    def getViewBox(self) -> _FakeViewBox:  # noqa: N802
        return _FakeViewBox()


class _FailingPgConstructor:
    def PlotWidget(self) -> Any:  # noqa: N802
        raise RuntimeError("plot init failed")


class _FailingPgUpdate:
    def PlotWidget(self) -> _FakePlotWidget:  # noqa: N802
        return _FakePlotWidget()

    def BarGraphItem(self, **_kwargs: object) -> object:  # noqa: N802
        raise RuntimeError("bar graph failed")


class _CapturingPg:
    def __init__(self) -> None:
        self.bar_kwargs: dict[str, object] | None = None

    def PlotWidget(self) -> _FakePlotWidget:  # noqa: N802
        return _FakePlotWidget()

    def BarGraphItem(self, **kwargs: object) -> object:  # noqa: N802
        self.bar_kwargs = kwargs
        return object()


@pytest.mark.parametrize("chart_class", [charts.TopMicrobesChart, charts.TrendChart])
def test_chart_falls_back_when_plot_widget_init_fails(monkeypatch, chart_class, qapp) -> None:
    monkeypatch.setattr(charts, "pg", _FailingPgConstructor())

    widget = chart_class()
    qapp.processEvents()

    fallback = widget.findChild(QLabel)
    assert fallback is not None
    assert fallback.text() == charts._CHART_FALLBACK_TEXT
    assert widget._plot is None
    widget.close()


@pytest.mark.parametrize(
    ("chart_class", "items"),
    [
        (charts.TopMicrobesChart, [("ECO - E. coli", 75.0)]),
        (charts.TrendChart, [("01.04.2026", 50.0)]),
    ],
)
def test_chart_update_data_ignores_runtime_plot_errors(monkeypatch, chart_class, items, qapp) -> None:
    monkeypatch.setattr(charts, "pg", _FailingPgUpdate())

    widget = chart_class()
    qapp.processEvents()

    widget.update_data(items)

    assert widget._items == items
    assert widget._plot is not None
    widget.close()


@pytest.mark.parametrize(
    ("chart_class", "items"),
    [
        (charts.TopMicrobesChart, [("ECO - E. coli", 75.0)]),
        (charts.TrendChart, [("01.04.2026", 50.0)]),
    ],
)
def test_chart_uses_theme_bar_brush(monkeypatch, chart_class, items, qapp) -> None:
    fake_pg = _CapturingPg()
    monkeypatch.setattr(charts, "pg", fake_pg)

    widget = chart_class()
    qapp.processEvents()

    widget.update_data(items)

    assert fake_pg.bar_kwargs is not None
    assert fake_pg.bar_kwargs["brush"] == charts._BAR_BRUSH
    widget.close()
