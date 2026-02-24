from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.services import reference_service as reference_service_module
from app.application.services.reference_service import ReferenceService
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.models_sqlalchemy import Base


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


def _seed_user(
    session_factory: Callable[[], AbstractContextManager[Session]],
    *,
    login: str,
    role: str,
) -> int:
    with session_factory() as session:
        user = models.User(
            login=login,
            password_hash="hash",
            role=role,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        session.add(user)
        session.flush()
        return int(user.id)


def test_reference_writes_require_admin_and_log_denial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = make_session_factory(tmp_path / "reference_acl.db")
    monkeypatch.setattr(reference_service_module, "session_scope", session_factory)
    service = ReferenceService()

    admin_id = _seed_user(session_factory, login="admin", role="admin")
    operator_id = _seed_user(session_factory, login="operator", role="operator")

    with pytest.raises(ValueError, match="Недостаточно прав"):
        service.add_department("ICU", actor_id=operator_id)

    with session_factory() as session:
        denied_rows = (
            session.query(models.AuditLog)
            .filter(models.AuditLog.entity_type == "reference")
            .filter(models.AuditLog.action == "access_denied")
            .all()
        )
    assert len(denied_rows) == 1
    assert denied_rows[0].user_id == operator_id

    service.add_department("ICU", actor_id=admin_id)
    departments = service.list_departments()
    assert len(departments) == 1
    assert departments[0].name == "ICU"
