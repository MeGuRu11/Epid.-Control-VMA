from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.exceptions import PermissionError as AppPermissionError
from app.application.services.saved_filter_service import SavedFilterService
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.models_sqlalchemy import Base
from app.infrastructure.db.repositories.user_repo import UserRepository


def make_session_factory(db_path: Path) -> Callable[[], AbstractContextManager[Session]]:
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


def seed_user(session_factory: Callable[[], AbstractContextManager[Session]]) -> int:
    repo = UserRepository()
    with session_factory() as session:
        user = repo.create(session, login="operator", password_hash="x", role="operator")
        session.flush()
        return cast(int, user.id)


def test_save_filter_requires_actor_id(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "saved_filter_requires_actor.db")
    service = SavedFilterService(session_factory=session_factory)

    with pytest.raises(AppPermissionError, match="actor_id"):
        service.save_filter(
            filter_type="analytics",
            name="Все случаи",
            payload={"department": "icu"},
            actor_id=cast(int, None),
        )


def test_save_filter_writes_actor_and_audit(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "saved_filter_audit.db")
    actor_id = seed_user(session_factory)
    service = SavedFilterService(session_factory=session_factory)

    saved = service.save_filter(
        filter_type="analytics",
        name="Все случаи",
        payload={"department": "icu"},
        actor_id=actor_id,
    )

    assert cast(int, saved.id) > 0
    with session_factory() as session:
        stored = session.query(models.SavedFilter).filter(models.SavedFilter.id == cast(int, saved.id)).one()
        audit = (
            session.query(models.AuditLog)
            .filter(
                models.AuditLog.entity_type == "saved_filter",
                models.AuditLog.entity_id == str(cast(int, saved.id)),
                models.AuditLog.action == "saved_filter_create",
            )
            .one_or_none()
        )

    assert cast(int | None, stored.created_by) == actor_id
    assert audit is not None
    assert cast(int | None, audit.user_id) == actor_id
