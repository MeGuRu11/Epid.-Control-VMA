from __future__ import annotations

from PySide6.QtWidgets import QLabel

from app.ui.widgets.transition_stack import TransitionStack


def test_transition_stack_switches_immediately_when_animation_disabled(qapp) -> None:
    stack = TransitionStack(animations_enabled=False)
    first = QLabel("first")
    second = QLabel("second")
    stack.addWidget(first)
    stack.addWidget(second)
    stack.setCurrentWidget(first)

    stack.setCurrentWidgetAnimated(second)

    assert stack.currentWidget() is second


def test_transition_stack_queues_last_target_while_busy(qapp) -> None:
    stack = TransitionStack(animations_enabled=True)
    first = QLabel("first")
    second = QLabel("second")
    third = QLabel("third")
    stack.addWidget(first)
    stack.addWidget(second)
    stack.addWidget(third)
    stack.setCurrentWidget(first)

    stack.setCurrentWidgetAnimated(second, direction=1)
    stack.setCurrentWidgetAnimated(third, direction=1)

    assert stack.currentWidget() is second
    assert stack._queued is not None
    assert stack._queued[0] is third
