from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.auth_dto import CreateUserRequest, LoginRequest
from app.application.services.auth_service import LOCKOUT_MINUTES, AuthService
from app.application.services.user_admin_service import UserAdminService
from app.infrastructure.db.models_sqlalchemy import Base, User
from app.infrastructure.db.repositories.user_repo import UserRepository


def make_session_factory(db_path: Path) -> Callable[[], AbstractContextManager[Session]]:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
    )

    @contextmanager
    def _session_scope() -> Iterator[Session]:
        session: Session = session_local()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return _session_scope


def test_create_and_login_user(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "auth.db")
    user_repo = UserRepository()

    admin_service = UserAdminService(session_factory=session_factory)
    auth_service = AuthService(session_factory=session_factory)

    # seed actor (system admin) manually
    with session_factory() as session:
        admin = user_repo.create(session, login="admin", password_hash="$2b$12$abcdefghijklmnopqrstuv", role="admin")
        session.flush()
        admin_id = cast(int, admin.id)

    req = CreateUserRequest(login="user1", password="StrongPass1", role="operator")
    new_id = admin_service.create_user(req, actor_id=admin_id)
    assert new_id > 0

    # login as created user
    session_ctx = auth_service.login(LoginRequest(login="user1", password="StrongPass1"))
    assert session_ctx.login == "user1"
    assert session_ctx.role == "operator"


def test_login_lockout_after_failed_attempts(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "auth_lockout.db")
    user_repo = UserRepository()
    admin_service = UserAdminService(session_factory=session_factory)

    current_time = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)

    def _clock() -> datetime:
        return current_time

    auth_service = AuthService(session_factory=session_factory, clock=_clock)

    with session_factory() as session:
        admin = user_repo.create(session, login="admin", password_hash="$2b$12$abcdefghijklmnopqrstuv", role="admin")
        session.flush()
        admin_id = cast(int, admin.id)

    req = CreateUserRequest(login="user1", password="StrongPass1", role="operator")
    admin_service.create_user(req, actor_id=admin_id)

    for _ in range(4):
        with pytest.raises(ValueError, match="Неверный логин или пароль"):
            auth_service.login(LoginRequest(login="user1", password="wrong-password"))

    with pytest.raises(ValueError, match="заблокирован"):
        auth_service.login(LoginRequest(login="user1", password="wrong-password"))

    with pytest.raises(ValueError, match="временно заблокирована"):
        auth_service.login(LoginRequest(login="user1", password="StrongPass1"))

    current_time += timedelta(minutes=LOCKOUT_MINUTES + 1)
    session_ctx = auth_service.login(LoginRequest(login="user1", password="StrongPass1"))
    assert session_ctx.login == "user1"
    assert session_ctx.role == "operator"

    with session_factory() as session:
        user = session.execute(select(User).where(User.login == "user1")).scalar_one()
        assert int(cast(int | None, user.failed_login_count) or 0) == 0
        assert user.locked_until is None
