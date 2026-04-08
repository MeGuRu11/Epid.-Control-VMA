from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

from app.application.dto.auth_dto import LoginRequest, SessionContext
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.infrastructure.db.repositories.user_repo import UserRepository
from app.infrastructure.db.session import session_scope
from app.infrastructure.security.password_hash import verify_password

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
        session_factory: Callable = session_scope,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.user_repo = user_repo or UserRepository()
        self.audit_repo = audit_repo or AuditLogRepository()
        self.session_factory = session_factory
        self.clock = clock or (lambda: datetime.now(UTC))

    def login(self, request: LoginRequest) -> SessionContext:
        now = self.clock()
        now = now.replace(tzinfo=UTC) if now.tzinfo is None else now.astimezone(UTC)
        error_message: str | None = None
        session_ctx: SessionContext | None = None

        with self.session_factory() as session:
            user = self.user_repo.get_by_login(session, request.login)
            if user is None or not bool(cast(bool, user.is_active)):
                error_message = "Неверный логин или пользователь деактивирован"
            else:
                locked_until = cast(datetime | None, user.locked_until)
                if locked_until is not None and locked_until.tzinfo is None:
                    locked_until = locked_until.replace(tzinfo=UTC)
                if locked_until is not None and locked_until > now:
                    remaining_seconds = max(0, int((locked_until - now).total_seconds()))
                    remaining_minutes = max(1, (remaining_seconds + 59) // 60)
                    error_message = (
                        f"Учетная запись временно заблокирована. Повторите попытку через {remaining_minutes} мин."
                    )
                else:
                    if locked_until is not None:
                        cast(Any, user).failed_login_count = 0
                        cast(Any, user).locked_until = None

                    password_hash = cast(str, user.password_hash)
                    if not verify_password(request.password, password_hash):
                        failed_attempts = int(cast(int | None, user.failed_login_count) or 0) + 1
                        cast(Any, user).failed_login_count = failed_attempts
                        if failed_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                            cast(Any, user).locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
                            error_message = (
                                f"Слишком много неудачных попыток. Доступ заблокирован на {LOCKOUT_MINUTES} минут."
                            )
                        else:
                            error_message = "Неверный логин или пароль"
                    else:
                        cast(Any, user).failed_login_count = 0
                        cast(Any, user).locked_until = None
                        self.audit_repo.add_event(
                            session,
                            user_id=cast(int, user.id),
                            entity_type="user",
                            entity_id=str(cast(int, user.id)),
                            action="login",
                            payload_json=json.dumps({"login": cast(str, user.login)}, ensure_ascii=False),
                        )
                        session_ctx = SessionContext(
                            user_id=cast(int, user.id),
                            login=cast(str, user.login),
                            role=cast(Literal["admin", "operator"], user.role),
                            created_at=now,
                        )

        if error_message is not None:
            raise ValueError(error_message)
        if session_ctx is None:
            raise RuntimeError("Не удалось создать сессию пользователя")
        return session_ctx
