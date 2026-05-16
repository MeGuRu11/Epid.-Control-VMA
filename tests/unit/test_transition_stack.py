from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QLabel, QWidget

from app.application.dto.auth_dto import SessionContext
from app.application.services.dashboard_service import DashboardService
from app.ui.home.home_view import HomeView
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


def test_transition_stack_uses_current_home_page_minimum_size_for_initial_layout(qapp) -> None:
    stack = TransitionStack(animations_enabled=False)
    current = HomeView(
        session=SessionContext(user_id=1, login="admin", role="admin"),
        dashboard_service=cast(
            DashboardService,
            SimpleNamespace(
                get_counts=lambda: {
                    "patients": 1,
                    "emr_cases": 2,
                    "lab_samples": 3,
                    "sanitary_samples": 4,
                },
                get_new_patients_count=lambda _days: 5,
                get_top_department_by_samples=lambda _days: ("ОРИТ", 6),
                get_last_login=lambda _user_id: None,
            ),
        ),
    )
    inactive_tall = QWidget()
    inactive_tall.setMinimumSize(QSize(960, 1820))

    stack.addWidget(current)
    stack.addWidget(inactive_tall)
    stack.setCurrentWidget(current)

    assert stack.minimumSizeHint().height() == current.minimumSizeHint().height()
    assert stack.minimumSizeHint().height() < inactive_tall.minimumSize().height()
