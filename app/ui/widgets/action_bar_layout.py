from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import QBoxLayout, QWidget


def update_action_bar_direction(
    layout: QBoxLayout,
    bar: QWidget,
    groups: Sequence[QWidget],
    *,
    extra_width: int = 24,
    available_width: int | None = None,
) -> None:
    visible_groups = [group for group in groups if group.isVisible()]
    if not visible_groups:
        target = QBoxLayout.Direction.LeftToRight
    else:
        required_width = sum(group.sizeHint().width() for group in visible_groups)
        required_width += max(0, len(visible_groups) - 1) * max(0, layout.spacing())
        required_width += max(0, extra_width)
        current_width = available_width if available_width is not None else bar.width()
        target = (
            QBoxLayout.Direction.LeftToRight
            if current_width >= required_width
            else QBoxLayout.Direction.TopToBottom
        )
    if layout.direction() != target:
        layout.setDirection(target)
