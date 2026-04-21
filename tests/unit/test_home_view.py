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
        top_department: tuple[str, int] | None = ("Кардиология", 9),
    ) -> None:
        self._last_login = last_login or datetime(2026, 4, 21, 7, 14, 10, tzinfo=UTC)
        self._fail_message = fail_message
        self._top_department = top_department

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
        return self._top_department


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


def test_home_view_shows_success_status_and_kpi_values_after_stats_load(qapp) -> None:
    view = HomeView(
        session=_make_session(role="admin"),
        dashboard_service=cast(Any, _DashboardServiceStub()),
    )
    view.show()
    qapp.processEvents()

    patients_summary = view._summary_widgets["patients"]
    top_department_summary = view._summary_widgets["top_department"]

    assert view.status_chip.text() == "Готово"
    assert view.status_chip.property("tone") == "success"
    assert view.status_label.isHidden() is True
    assert view.last_login_label.text() == "21.04.2026 07:14:10"
    assert view.last_refresh_label.text() != "-"
    assert patients_summary.value_label.text() == "12"
    assert patients_summary.detail_label.text() == "зарегистрировано в системе"
    assert top_department_summary.value_label.text() == "Кардиология"
    assert top_department_summary.detail_label.text() == "9 санитарных проб за 30 дней"


def test_home_view_shows_top_department_fallback_when_no_data(qapp) -> None:
    view = HomeView(
        session=_make_session(role="admin"),
        dashboard_service=cast(Any, _DashboardServiceStub(top_department=None)),
    )
    view.show()
    qapp.processEvents()

    top_department_summary = view._summary_widgets["top_department"]

    assert top_department_summary.value_label.text() == "Нет данных"
    assert top_department_summary.detail_label.text() == "Нет данных"


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


def test_home_view_uses_equal_height_hero_layout_on_wide_screens(qapp) -> None:
    view = HomeView(
        session=_make_session(role="admin"),
        dashboard_service=cast(Any, _DashboardServiceStub()),
    )
    view.show()
    qapp.processEvents()

    view.resize(1600, 900)
    qapp.processEvents()

    assert view._hero_layout.direction() == QBoxLayout.Direction.LeftToRight
    assert abs(view._hero_card.height() - view._utility_card.height()) <= 2


def test_home_view_switches_to_vertical_hero_layout_on_narrow_screens(qapp) -> None:
    view = HomeView(
        session=_make_session(role="admin"),
        dashboard_service=cast(Any, _DashboardServiceStub()),
    )
    view.show()
    qapp.processEvents()

    view.resize(420, 900)
    qapp.processEvents()

    assert view._hero_layout.direction() == QBoxLayout.Direction.TopToBottom


def test_home_view_reflows_summary_grid_to_three_two_and_one_columns(qapp) -> None:
    view = HomeView(
        session=_make_session(role="admin"),
        dashboard_service=cast(Any, _DashboardServiceStub()),
    )
    view.show()
    qapp.processEvents()

    view.resize(1600, 900)
    qapp.processEvents()
    assert view._summary_columns == 3

    found_two_columns = False
    for width in range(900, 420, -20):
        view.resize(width, 900)
        qapp.processEvents()
        if view._summary_columns == 2:
            found_two_columns = True
            break

    assert found_two_columns is True

    found_one_column = False
    for width in range(420, 280, -20):
        view.resize(width, 900)
        qapp.processEvents()
        if view._summary_columns == 1:
            found_one_column = True
            break

    assert found_one_column is True
