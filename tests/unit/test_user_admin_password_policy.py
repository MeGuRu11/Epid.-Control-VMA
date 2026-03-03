"""Tests for password policy enforcement in UserAdminService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.application.dto.auth_dto import CreateUserRequest, ResetPasswordRequest
from app.application.services.user_admin_service import MIN_PASSWORD_LENGTH, UserAdminService


@pytest.fixture()
def service() -> UserAdminService:
    return UserAdminService(
        user_repo=MagicMock(),
        audit_repo=MagicMock(),
        session_factory=MagicMock(),
    )


def test_create_user_dto_rejects_short_password() -> None:
    """Pydantic DTO rejects passwords shorter than 8 characters."""
    with pytest.raises(ValidationError, match="string_too_short"):
        CreateUserRequest(login="testuser", password="short", role="operator")


def test_create_user_accepts_valid_password(service: UserAdminService) -> None:
    request = CreateUserRequest(login="testuser", password="a" * MIN_PASSWORD_LENGTH, role="operator")
    mock_session = MagicMock()
    service.session_factory.return_value.__enter__ = MagicMock(return_value=mock_session)
    service.session_factory.return_value.__exit__ = MagicMock(return_value=False)

    admin_user = MagicMock()
    admin_user.role = "admin"
    service.user_repo.get_by_id.return_value = admin_user
    service.user_repo.get_by_login.return_value = None

    created_user = MagicMock()
    created_user.id = 42
    service.user_repo.create.return_value = created_user

    with patch("app.application.services.user_admin_service.hash_password", return_value="hashed"):
        result = service.create_user(request, actor_id=1)

    assert result == 42


def test_reset_password_dto_rejects_short_password() -> None:
    """Pydantic DTO rejects passwords shorter than 8 characters."""
    with pytest.raises(ValidationError, match="string_too_short"):
        ResetPasswordRequest(user_id=2, new_password="abc", deactivate=False)


def test_reset_password_accepts_valid_password(service: UserAdminService) -> None:
    request = ResetPasswordRequest(user_id=2, new_password="b" * MIN_PASSWORD_LENGTH, deactivate=False)
    mock_session = MagicMock()
    service.session_factory.return_value.__enter__ = MagicMock(return_value=mock_session)
    service.session_factory.return_value.__exit__ = MagicMock(return_value=False)

    admin_user = MagicMock()
    admin_user.role = "admin"
    service.user_repo.get_by_id.return_value = admin_user

    target_user = MagicMock()
    target_user.id = 2
    service.user_repo.get_by_id.return_value = admin_user

    with patch("app.application.services.user_admin_service.hash_password", return_value="hashed"):
        service.reset_password(request, actor_id=1)  # should not raise


def test_min_password_length_constant() -> None:
    assert MIN_PASSWORD_LENGTH == 8

