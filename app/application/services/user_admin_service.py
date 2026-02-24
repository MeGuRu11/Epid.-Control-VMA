from __future__ import annotations

import json
from collections.abc import Callable
from typing import cast

from app.application.dto.auth_dto import CreateUserRequest, ResetPasswordRequest
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.infrastructure.db.repositories.user_repo import UserRepository
from app.infrastructure.db.session import session_scope
from app.infrastructure.security.password_hash import hash_password


class UserAdminService:
    def __init__(
        self,
        user_repo: UserRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
        session_factory: Callable = session_scope,
    ) -> None:
        self.user_repo = user_repo or UserRepository()
        self.audit_repo = audit_repo or AuditLogRepository()
        self.session_factory = session_factory

    def create_user(self, request: CreateUserRequest, actor_id: int) -> int:
        with self.session_factory() as session:
            self._require_admin(session, actor_id)
            existing = self.user_repo.get_by_login(session, request.login)
            if existing:
                raise ValueError("Логин уже существует")

            hashed = hash_password(request.password, scheme="argon2")
            user = self.user_repo.create(session, login=request.login, password_hash=hashed, role=request.role)

            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="user",
                entity_id=str(user.id),
                action="create_user",
                payload_json=json.dumps({"login": request.login, "role": request.role}),
            )
            return cast(int, user.id)

    def reset_password(self, request: ResetPasswordRequest, actor_id: int) -> None:
        with self.session_factory() as session:
            self._require_admin(session, actor_id)
            user = self.user_repo.get_by_id(session, request.user_id)
            if not user:
                raise ValueError("Пользователь не найден")

            hashed = hash_password(request.new_password, scheme="argon2")
            self.user_repo.set_password(session, request.user_id, hashed)
            if request.deactivate:
                self.user_repo.set_active(session, request.user_id, False)

            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="user",
                entity_id=str(request.user_id),
                action="reset_password",
                payload_json=json.dumps({"deactivate": request.deactivate}),
            )

    def set_active(self, user_id: int, is_active: bool, actor_id: int) -> None:
        with self.session_factory() as session:
            self._require_admin(session, actor_id)
            user = self.user_repo.get_by_id(session, user_id)
            if not user:
                raise ValueError("Пользователь не найден")
            self.user_repo.set_active(session, user_id, is_active)
            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="user",
                entity_id=str(user_id),
                action="set_active",
                payload_json=json.dumps({"is_active": is_active}),
            )

    def list_users(self, query: str | None = None) -> list:
        with self.session_factory() as session:
            return self.user_repo.list_users(session, query=query)

    def _require_admin(self, session, actor_id: int) -> None:
        actor = self.user_repo.get_by_id(session, actor_id)
        if not actor or actor.role != "admin":
            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="user",
                entity_id=str(actor_id),
                action="access_denied",
                payload_json=json.dumps({"reason": "admin_required"}),
            )
            raise ValueError("Недостаточно прав для операции")
