from __future__ import annotations

from typing import Any


def test_trend_positive_metric_growth_is_green(qtbot: Any) -> None:
    from app.ui.analytics.widgets.trend_indicator import TrendIndicator

    indicator = TrendIndicator(metric_kind="positive")
    qtbot.addWidget(indicator)

    indicator.set_change(112, 100)

    assert indicator.text() == "▲ 12.0%"
    assert indicator.objectName() == "kpiTrendUp"


def test_trend_positive_metric_decline_is_red(qtbot: Any) -> None:
    from app.ui.analytics.widgets.trend_indicator import TrendIndicator

    indicator = TrendIndicator(metric_kind="positive")
    qtbot.addWidget(indicator)

    indicator.set_change(95, 100)

    assert indicator.text() == "▼ 5.0%"
    assert indicator.objectName() == "kpiTrendDown"


def test_trend_negative_metric_growth_is_red(qtbot: Any) -> None:
    from app.ui.analytics.widgets.trend_indicator import TrendIndicator

    indicator = TrendIndicator(metric_kind="negative")
    qtbot.addWidget(indicator)

    indicator.set_change(12, 10)

    assert indicator.text() == "▲ 20.0%"
    assert indicator.objectName() == "kpiTrendDown"


def test_trend_neutral_metric_always_flat(qtbot: Any) -> None:
    from app.ui.analytics.widgets.trend_indicator import TrendIndicator

    indicator = TrendIndicator(metric_kind="neutral")
    qtbot.addWidget(indicator)

    indicator.set_change(150, 100)

    assert indicator.text() == "▲ 50.0%"
    assert indicator.objectName() == "kpiTrendFlat"


def test_trend_zero_previous_shows_dash(qtbot: Any) -> None:
    from app.ui.analytics.widgets.trend_indicator import TrendIndicator

    indicator = TrendIndicator(metric_kind="positive")
    qtbot.addWidget(indicator)

    indicator.set_change(10, 0)

    assert indicator.text() == "—"
    assert indicator.objectName() == "kpiTrendFlat"


def test_trend_none_previous_shows_dash(qtbot: Any) -> None:
    from app.ui.analytics.widgets.trend_indicator import TrendIndicator

    indicator = TrendIndicator(metric_kind="positive")
    qtbot.addWidget(indicator)

    indicator.set_change(10, None)

    assert indicator.text() == "—"
    assert indicator.objectName() == "kpiTrendFlat"


def test_trend_tiny_change_shows_dash(qtbot: Any) -> None:
    from app.ui.analytics.widgets.trend_indicator import TrendIndicator

    indicator = TrendIndicator(metric_kind="positive")
    qtbot.addWidget(indicator)

    indicator.set_change(100.4, 100)

    assert indicator.text() == "—"
    assert indicator.objectName() == "kpiTrendFlat"
