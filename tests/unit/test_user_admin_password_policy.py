"""Tests for password policy enforcement in UserAdminService."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.auth_dto import CreateUserRequest, ResetPasswordRequest
from app.application.services.user_admin_service import MIN_PASSWORD_LENGTH, UserAdminService
from app.infrastructure.db.models_sqlalchemy import AuditLog, Base, User


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


@pytest.fixture()
def service_context(tmp_path: Path) -> tuple[UserAdminService, Callable[[], AbstractContextManager[Session]], int]:
    session_factory = _make_session_factory(tmp_path / "user_admin_policy.db")
    with session_factory() as session:
        admin = User(login="admin", password_hash="seed-hash", role="admin", is_active=True)
        session.add(admin)
        session.flush()
        admin_id = cast(int, admin.id)
    service = UserAdminService(session_factory=session_factory)
    return service, session_factory, admin_id


def test_create_user_dto_rejects_short_password() -> None:
    """Pydantic DTO rejects passwords shorter than 8 characters."""
    with pytest.raises(ValidationError, match="string_too_short"):
        CreateUserRequest(login="testuser", password="short", role="operator")


def test_create_user_accepts_valid_password(
    service_context: tuple[UserAdminService, Callable[[], AbstractContextManager[Session]], int],
) -> None:
    service, session_factory, admin_id = service_context
    request = CreateUserRequest(login="testuser", password="a" * MIN_PASSWORD_LENGTH, role="operator")
    with patch("app.application.services.user_admin_service.hash_password", return_value="hashed-password"):
        result = service.create_user(request, actor_id=admin_id)

    assert result > 0
    with session_factory() as session:
        created = session.execute(select(User).where(User.id == result)).scalar_one()
        assert created.login == "testuser"
        assert created.role == "operator"
        assert created.password_hash == "hashed-password"

        audit_entry = session.execute(
            select(AuditLog).where(AuditLog.entity_id == str(result), AuditLog.action == "create_user")
        ).scalar_one_or_none()
        assert audit_entry is not None


def test_reset_password_dto_rejects_short_password() -> None:
    """Pydantic DTO rejects passwords shorter than 8 characters."""
    with pytest.raises(ValidationError, match="string_too_short"):
        ResetPasswordRequest(user_id=2, new_password="abc", deactivate=False)


def test_reset_password_accepts_valid_password(
    service_context: tuple[UserAdminService, Callable[[], AbstractContextManager[Session]], int],
) -> None:
    service, session_factory, admin_id = service_context
    with session_factory() as session:
        target_user = User(login="operator", password_hash="old-hash", role="operator", is_active=True)
        session.add(target_user)
        session.flush()
        target_user_id = cast(int, target_user.id)

    request = ResetPasswordRequest(
        user_id=target_user_id,
        new_password="b" * MIN_PASSWORD_LENGTH,
        deactivate=True,
    )
    with patch("app.application.services.user_admin_service.hash_password", return_value="new-hash"):
        service.reset_password(request, actor_id=admin_id)

    with session_factory() as session:
        updated = session.execute(select(User).where(User.id == target_user_id)).scalar_one()
        assert updated.password_hash == "new-hash"
        assert updated.is_active is False

        audit_entry = session.execute(
            select(AuditLog).where(
                AuditLog.entity_id == str(target_user_id),
                AuditLog.action == "reset_password",
            )
        ).scalar_one_or_none()
        assert audit_entry is not None


def test_min_password_length_constant() -> None:
    assert MIN_PASSWORD_LENGTH == 8

