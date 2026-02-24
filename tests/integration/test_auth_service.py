from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import cast

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.auth_dto import CreateUserRequest, LoginRequest
from app.application.services.auth_service import AuthService
from app.application.services.user_admin_service import UserAdminService
from app.infrastructure.db.models_sqlalchemy import Base
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
