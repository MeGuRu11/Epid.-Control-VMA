from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from PySide6.QtWidgets import QBoxLayout

from app.application.dto.auth_dto import SessionContext
from app.ui.home.home_view import HomeView


class _DashboardServiceStub:
    def __init__(
        self,
        *,
        last_login: datetime | None = None,
        fail_message: str | None = None,
    ) -> None:
        self._last_login = last_login or datetime(2026, 4, 21, 7, 14, 10, tzinfo=UTC)
        self._fail_message = fail_message

    def get_counts(self) -> dict[str, int]:
        if self._fail_message is not None:
            raise ValueError(self._fail_message)
        return {
            "patients": 12,
            "emr_cases": 7,
            "lab_samples": 5,
            "sanitary_samples": 3,
        }

    def get_last_login(self, _user_id: int) -> datetime | None:
        return self._last_login

    def get_new_patients_count(self, _days: int) -> int:
        return 4

    def get_top_department_by_samples(self, _days: int) -> tuple[str, int] | None:
        return ("Кардиология", 9)


def _make_session(login: str = "admin", role: str = "admin") -> SessionContext:
    return cast(
        SessionContext,
        SessionContext(user_id=1, login=login, role=cast(Any, role)),
    )


def test_home_view_localizes_role_labels(qapp) -> None:
    view = HomeView(
        session=_make_session(role="admin"),
        dashboard_service=cast(Any, _DashboardServiceStub()),
    )
    view.show()
    qapp.processEvents()

    assert view._role_badge.text() == "Администратор"
    assert view._format_role_label("operator") == "Оператор"
    assert view._format_role_label("guest") == "guest"


def test_home_view_shows_success_status_after_stats_load(qapp) -> None:
    view = HomeView(
        session=_make_session(role="admin"),
        dashboard_service=cast(Any, _DashboardServiceStub()),
    )
    view.show()
    qapp.processEvents()

    assert view.status_chip.text() == "Готово"
    assert view.status_chip.property("tone") == "success"
    assert view.status_label.isHidden() is True
    assert view.last_login_label.text() == "21.04.2026 07:14:10"
    assert view.last_refresh_label.text() != "-"


def test_home_view_shows_error_status_when_stats_fail(qapp) -> None:
    view = HomeView(
        session=_make_session(role="admin"),
        dashboard_service=cast(Any, _DashboardServiceStub(fail_message="сервис недоступен")),
    )
    view.show()
    qapp.processEvents()

    assert view.status_chip.text() == "Ошибка загрузки"
    assert view.status_chip.property("tone") == "error"
    assert view.status_label.isHidden() is False
    assert "Ошибка: сервис недоступен" in view.status_label.text()


def test_home_view_set_session_updates_user_block(qapp) -> None:
    view = HomeView(
        session=_make_session(login="admin", role="admin"),
        dashboard_service=cast(Any, _DashboardServiceStub()),
    )
    view.show()
    qapp.processEvents()

    view.set_session(_make_session(login="operator1", role="operator"))
    qapp.processEvents()

    assert view._user_name_label.text() == "operator1"
    assert view._role_badge.text() == "Оператор"
    assert view.status_chip.text() == "Готово"


def test_home_view_uses_responsive_hero_layout(qapp) -> None:
    view = HomeView(
        session=_make_session(role="admin"),
        dashboard_service=cast(Any, _DashboardServiceStub()),
    )
    view.show()
    qapp.processEvents()

    view.resize(1600, 900)
    qapp.processEvents()
    assert view._hero_layout.direction() == QBoxLayout.Direction.LeftToRight

    view.resize(420, 900)
    qapp.processEvents()
    assert view._hero_layout.direction() == QBoxLayout.Direction.TopToBottom
