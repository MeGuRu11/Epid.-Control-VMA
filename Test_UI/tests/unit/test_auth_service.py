from __future__ import annotations

from app.application.dto.auth_dto import UserCreateIn
from app.application.services.auth_service import AuthService


def test_auth_login_flow(engine):
    auth = AuthService(engine)
    assert auth.is_first_run() is True
    auth.create_initial_admin("admin", "admin1234")
    assert auth.is_first_run() is False

    session = auth.login("admin", "admin1234")
    assert session is not None
    assert session.role == "admin"


def test_auth_create_user_admin_only(engine, admin_session, operator_session):
    auth = AuthService(engine)
    auth.create_initial_admin("admin", "admin1234")
    user_id = auth.create_user(UserCreateIn(login="operator", password="operator123", role="operator"), admin_session)
    assert user_id > 0

    denied = False
    try:
        auth.create_user(UserCreateIn(login="x", password="x123456", role="operator"), operator_session)
    except PermissionError:
        denied = True
    assert denied is True

