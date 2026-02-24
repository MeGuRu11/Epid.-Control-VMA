from __future__ import annotations

import json
from collections.abc import Callable
from typing import Literal, cast

from app.application.dto.auth_dto import LoginRequest, SessionContext
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.infrastructure.db.repositories.user_repo import UserRepository
from app.infrastructure.db.session import session_scope
from app.infrastructure.security.password_hash import verify_password


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
        session_factory: Callable = session_scope,
    ) -> None:
        self.user_repo = user_repo or UserRepository()
        self.audit_repo = audit_repo or AuditLogRepository()
        self.session_factory = session_factory

    def login(self, request: LoginRequest) -> SessionContext:
        with self.session_factory() as session:
            user = self.user_repo.get_by_login(session, request.login)
            if not user or not user.is_active:
                raise ValueError("Неверный логин или пользователь деактивирован")

            password_hash = cast(str, user.password_hash)
            if not verify_password(request.password, password_hash):
                raise ValueError("Неверный логин или пароль")

            self.audit_repo.add_event(
                session,
                user_id=cast(int, user.id),
                entity_type="user",
                entity_id=str(cast(int, user.id)),
                action="login",
                payload_json=json.dumps({"login": cast(str, user.login)}),
            )
            return SessionContext(
                user_id=cast(int, user.id),
                login=cast(str, user.login),
                role=cast(Literal["admin", "operator"], user.role),
            )
