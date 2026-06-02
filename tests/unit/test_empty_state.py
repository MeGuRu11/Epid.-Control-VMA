from __future__ import annotations

from typing import Any, cast

from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget


class _ReportsControllerStub:
    def load_report_history(self, **_kwargs: object) -> list[Any]:
        return []


def _assert_wrapped_labels_fit(widget: QWidget) -> None:
    labels = cast(list[QLabel], widget.findChildren(QLabel))
    wrapped_labels = [label for label in labels if label.wordWrap()]
    assert wrapped_labels
    for label in wrapped_labels:
        assert label.width() > 0
        needed = label.heightForWidth(label.width())
        assert needed >= 0
        assert label.height() >= needed, (
            f"{label.objectName() or label.text()}: "
            f"height={label.height()}, needed={needed}, width={label.width()}"
        )


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


def test_empty_state_expands_to_wrapped_label_height_under_theme(qtbot: Any, qapp: Any) -> None:
    from app.config import Settings
    from app.ui.analytics.widgets.empty_state import EmptyState
    from app.ui.theme import apply_theme

    apply_theme(qapp, Settings())
    state = EmptyState(
        "История отчётов пуста после применения фильтров и проверки сформированных артефактов.",
        "Здесь появятся сформированные отчёты. Измените параметры поиска или сбросьте фильтры.",
    )
    qtbot.addWidget(state)

    state.resize(320, state.minimumHeight())
    state.show()
    qapp.processEvents()

    _assert_wrapped_labels_fit(state)


def test_reports_empty_state_labels_fit_after_history_is_loaded(qtbot: Any, qapp: Any) -> None:
    from app.ui.analytics.tabs.reports_tab import ReportsTab

    tab = ReportsTab(cast(Any, _ReportsControllerStub()))
    qtbot.addWidget(tab)
    tab.show()

    for width in (1120, 520):
        tab.resize(width, 620)
        tab.load_report_history()
        qapp.processEvents()

        assert tab._empty_state.isVisible()
        assert not tab.report_history_table.isVisible()
        _assert_wrapped_labels_fit(tab._empty_state)
