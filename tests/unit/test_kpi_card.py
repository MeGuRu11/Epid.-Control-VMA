from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt


def test_kpi_card_instantiates(qtbot: Any) -> None:
    from app.ui.analytics.widgets.kpi_card import KpiCard

    card = KpiCard("Госпитализаций", "Г", "neutral", "neutral")
    qtbot.addWidget(card)

    assert card.objectName() == "kpiCard"


def test_kpi_card_set_value_updates_label(qtbot: Any) -> None:
    from app.ui.analytics.widgets.kpi_card import KpiCard

    card = KpiCard("Положительных", "Л", "lab", "neutral")
    qtbot.addWidget(card)

    card.set_value("42 (12.5%)")

    assert card._value.text() == "42 (12.5%)"


def test_kpi_card_clicked_signal_emits(qtbot: Any) -> None:
    from app.ui.analytics.widgets.kpi_card import KpiCard

    card = KpiCard("Превалентность", "%", "calc", "negative")
    qtbot.addWidget(card)

    emitted: list[bool] = []
    card.clicked.connect(lambda: emitted.append(True))
    qtbot.mouseClick(card, Qt.MouseButton.LeftButton)

    assert emitted == [True]


def test_kpi_card_with_sparkline_has_widget(qtbot: Any) -> None:
    from app.ui.analytics.widgets.kpi_card import KpiCard
    from app.ui.analytics.widgets.sparkline import Sparkline

    card = KpiCard("Госпитализаций", "Г", "neutral", "neutral", show_sparkline=True)
    qtbot.addWidget(card)

    assert card.findChild(Sparkline) is card._sparkline


def test_kpi_card_without_sparkline_has_no_widget(qtbot: Any) -> None:
    from app.ui.analytics.widgets.kpi_card import KpiCard
    from app.ui.analytics.widgets.sparkline import Sparkline

    card = KpiCard("Случаев ИСМП", "И", "negative", "negative", show_sparkline=False)
    qtbot.addWidget(card)

    assert card._sparkline is None
    assert card.findChild(Sparkline) is None


def test_kpi_card_set_sparkline_data_does_not_raise(qtbot: Any) -> None:
    from app.ui.analytics.widgets.kpi_card import KpiCard

    card = KpiCard("Положительных", "Л", "lab", "neutral", show_sparkline=True)
    qtbot.addWidget(card)

    card.set_sparkline_data([1, 2, 5])

    assert card._sparkline is not None
    assert card._sparkline._values == [1.0, 2.0, 5.0]
