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
