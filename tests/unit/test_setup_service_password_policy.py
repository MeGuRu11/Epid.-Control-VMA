from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.services.setup_service import MIN_PASSWORD_LENGTH, SetupService
from app.infrastructure.db.models_sqlalchemy import Base, User


def _make_session_factory(db_path: Path) -> Callable[[], AbstractContextManager[Session]]:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
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


def test_create_initial_user_rejects_short_password(tmp_path: Path) -> None:
    service = SetupService(session_factory=_make_session_factory(tmp_path / "setup_short.db"))

    with pytest.raises(ValueError, match="не менее"):
        service.create_initial_user(login="admin", password="123")


def test_create_initial_user_accepts_valid_password(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "setup_ok.db")
    service = SetupService(session_factory=session_factory)

    with patch("app.application.services.setup_service.hash_password", return_value="hashed-password"):
        service.create_initial_user(login="admin", password="a" * MIN_PASSWORD_LENGTH)

    with session_factory() as session:
        user = session.execute(select(User).where(User.login == "admin")).scalar_one()
        assert user.role == "admin"
        assert user.password_hash == "hashed-password"
