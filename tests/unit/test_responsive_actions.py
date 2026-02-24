from __future__ import annotations

from PySide6.QtWidgets import QPushButton

from app.ui.widgets.responsive_actions import ResponsiveActionsPanel


def test_responsive_actions_reflow_changes_columns_by_width(qapp) -> None:
    panel = ResponsiveActionsPanel(min_button_width=100, max_columns=4)
    buttons = [QPushButton(f"b{i}") for i in range(4)]
    panel.set_buttons(buttons)

    panel.resize(260, 120)
    qapp.processEvents()
    narrow_columns = panel._columns_for_width()

    panel.resize(600, 120)
    qapp.processEvents()
    wide_columns = panel._columns_for_width()

    assert narrow_columns < wide_columns


def test_responsive_actions_compact_mode_reduces_min_width(qapp) -> None:
    panel = ResponsiveActionsPanel(min_button_width=120, max_columns=4)
    button = QPushButton("A")
    panel.set_buttons([button])
    regular_min = button.minimumWidth()

    panel.set_compact(True)
    compact_min = button.minimumWidth()

    assert compact_min < regular_min
