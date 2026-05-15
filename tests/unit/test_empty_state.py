from __future__ import annotations

from typing import Any, cast

from PySide6.QtWidgets import QLabel


def test_empty_state_instantiates(qtbot: Any) -> None:
    from app.ui.analytics.widgets.empty_state import EmptyState

    state = EmptyState("No data")
    qtbot.addWidget(state)
    label = state.findChild(QLabel)

    assert label is not None
    assert label.text() == "No data"


def test_empty_state_with_hint(qtbot: Any) -> None:
    from app.ui.analytics.widgets.empty_state import EmptyState

    state = EmptyState("No data", "Change filters")
    qtbot.addWidget(state)

    label_widgets = cast(list[QLabel], state.findChildren(QLabel))
    labels = [label.text() for label in label_widgets]
    assert labels == ["No data", "Change filters"]


def test_empty_state_visible_by_default(qtbot: Any) -> None:
    from app.ui.analytics.widgets.empty_state import EmptyState

    state = EmptyState()
    qtbot.addWidget(state)

    state.show()

    assert state.isVisible()
