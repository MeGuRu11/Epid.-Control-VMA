from __future__ import annotations

from typing import Any, cast

from PySide6.QtWidgets import QProgressBar


def test_donut_chart_instantiates(qtbot: Any) -> None:
    from app.ui.analytics.widgets.donut_chart import DonutChart

    chart = DonutChart()
    qtbot.addWidget(chart)

    assert chart is not None


def test_donut_chart_set_data_no_crash(qtbot: Any) -> None:
    from app.ui.analytics.widgets.donut_chart import DonutChart, DonutSegment

    chart = DonutChart()
    qtbot.addWidget(chart)

    chart.set_data([("ВАП", 2), ("ИОХВ", 1)])

    assert len(cast(list[DonutSegment], chart.findChildren(DonutSegment))) == 2


def test_donut_chart_empty_data_no_crash(qtbot: Any) -> None:
    from app.ui.analytics.widgets.donut_chart import DonutChart, DonutSegment

    chart = DonutChart()
    qtbot.addWidget(chart)

    chart.set_data([])

    assert chart.findChildren(DonutSegment) == []


def test_donut_canvas_paints_without_crash(qtbot: Any) -> None:
    from app.ui.analytics.widgets.donut_chart import DonutCanvas

    canvas = DonutCanvas()
    qtbot.addWidget(canvas)

    canvas.set_data([("ВАП", 2, "#6FB9AD"), ("ИОХВ", 1, "#F59E0B")])
    canvas.repaint()

    assert canvas.width() >= 180


def test_ismp_department_bar_set_data(qtbot: Any) -> None:
    from app.ui.analytics.widgets.donut_chart import IsmpDepartmentBar

    widget = IsmpDepartmentBar()
    qtbot.addWidget(widget)

    widget.set_data([("ICU", 3), ("Surgery", 1)])

    bars = cast(list[QProgressBar], widget.findChildren(QProgressBar))
    assert len(bars) == 2
    assert bars[0].value() == 3


def test_ismp_department_bar_empty_data(qtbot: Any) -> None:
    from app.ui.analytics.widgets.donut_chart import IsmpDepartmentBar

    widget = IsmpDepartmentBar()
    qtbot.addWidget(widget)

    widget.set_data([])

    assert widget.findChildren(QProgressBar) == []


def test_ismp_department_bar_limits_to_max_n(qtbot: Any) -> None:
    from app.ui.analytics.widgets.donut_chart import IsmpDepartmentBar

    widget = IsmpDepartmentBar()
    qtbot.addWidget(widget)
    data = [(f"Dept {idx}", idx) for idx in range(10, 0, -1)]

    widget.set_data(data, max_n=4)

    assert len(cast(list[QProgressBar], widget.findChildren(QProgressBar))) == 4
