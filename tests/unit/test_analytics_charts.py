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
        self.items: list[object] = []

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
        self.items.append(_item)

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


def test_build_axis_ticks_returns_empty_for_empty_labels() -> None:
    assert charts.build_axis_ticks([]) == []


def test_build_axis_ticks_keeps_short_period_complete() -> None:
    labels = [f"{day:02d}.04.2026" for day in range(1, 6)]

    assert charts.build_axis_ticks(labels, max_labels=10) == list(enumerate(labels))


def test_build_axis_ticks_thins_long_period_and_keeps_edges() -> None:
    labels = [f"{day:02d}.04.2026" for day in range(1, 22)]

    ticks = charts.build_axis_ticks(labels, max_labels=10)
    indexes = [index for index, _label in ticks]

    assert len(ticks) <= 10
    assert ticks[0] == (0, "01.04.2026")
    assert ticks[-1] == (20, "21.04.2026")
    assert indexes == sorted(indexes)
    assert len(indexes) == len(set(indexes))


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


def test_trend_chart_keeps_all_points_and_thins_long_axis_ticks(monkeypatch, qapp) -> None:
    fake_pg = _CapturingPg()
    monkeypatch.setattr(charts, "pg", fake_pg)
    items = [(f"{day:02d}.04.2026", float(day)) for day in range(1, 31)]

    widget = charts.TrendChart()
    qapp.processEvents()

    widget.update_data(items)

    assert fake_pg.bar_kwargs is not None
    assert fake_pg.bar_kwargs["x"] == list(range(30))
    assert fake_pg.bar_kwargs["height"] == [float(day) for day in range(1, 31)]
    plot = widget._plot
    assert plot is not None
    ticks = plot.axis.ticks[0]
    assert len(ticks) <= charts.DEFAULT_MAX_X_AXIS_LABELS
    assert len(ticks) < len(items)
    assert ticks[0] == (0, "01.04.2026")
    assert ticks[-1] == (29, "30.04.2026")
    widget.close()


def test_trend_chart_keeps_short_axis_ticks_complete(monkeypatch, qapp) -> None:
    fake_pg = _CapturingPg()
    monkeypatch.setattr(charts, "pg", fake_pg)
    items = [(f"{day:02d}.04.2026", float(day)) for day in range(1, 8)]

    widget = charts.TrendChart()
    qapp.processEvents()

    widget.update_data(items)

    plot = widget._plot
    assert plot is not None
    assert plot.axis.ticks[0] == list(enumerate([label for label, _value in items]))
    widget.close()
