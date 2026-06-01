from __future__ import annotations

from typing import Any, cast

from PySide6.QtWidgets import QLabel, QSizePolicy


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


def test_empty_state_with_hint_has_room_for_wrapped_text(qtbot: Any) -> None:
    from app.ui.analytics.widgets.empty_state import EmptyState

    state = EmptyState("No results found for this query.", "Try changing the search filters.")
    qtbot.addWidget(state)

    assert state.minimumHeight() >= 100
    assert state.sizePolicy().verticalPolicy() == QSizePolicy.Policy.MinimumExpanding
    label_widgets = cast(list[QLabel], state.findChildren(QLabel))
    for label in label_widgets:
        assert label.wordWrap()


def test_empty_state_has_enough_height_for_wrapped_title_and_hint(qtbot: Any) -> None:
    from PySide6.QtWidgets import QFrame

    from app.ui.analytics.widgets.empty_state import EmptyState

    state = EmptyState("История отчётов пуста.", "Здесь появятся сформированные отчёты.")
    qtbot.addWidget(state)

    frame = state.findChild(QFrame, "emptyState")
    assert frame is not None
    assert state.minimumHeight() >= 132
    assert frame.minimumHeight() >= 132
    label_widgets = cast(list[QLabel], state.findChildren(QLabel))
    assert all(label.wordWrap() for label in label_widgets)
