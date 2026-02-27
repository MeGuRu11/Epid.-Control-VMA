from __future__ import annotations

import time
from dataclasses import dataclass

from ...application.dto.auth_dto import SessionOut, UserCreateIn
from ...infrastructure.audit.audit_logger import AuditEvent, AuditLogger
from ...infrastructure.db.repositories.user_repo import UserRepo
from ...infrastructure.security.password_hash import hash_password, verify_password


@dataclass(frozen=True)
class SessionContext:
    user_id: int
    login: str
    role: str


_LOCKOUT_THRESHOLD = 5
_LOCKOUT_WINDOW = 900.0  # 15 минут


class AuthService:
    def __init__(self, engine):
        self._audit = AuditLogger(engine)
        self._users = UserRepo(engine)
        self._failed: dict[str, list[float]] = {}

    def record_failure(self, login: str) -> None:
        now = time.time()
        attempts = [t for t in self._failed.get(login, []) if now - t < _LOCKOUT_WINDOW]
        attempts.append(now)
        self._failed[login] = attempts

    def is_locked(self, login: str) -> tuple[bool, int]:
        now = time.time()
        attempts = [t for t in self._failed.get(login, []) if now - t < _LOCKOUT_WINDOW]
        self._failed[login] = attempts
        if len(attempts) >= _LOCKOUT_THRESHOLD:
            unlock_at = min(attempts) + _LOCKOUT_WINDOW
            return True, max(0, int(unlock_at - now))
        return False, 0

    def is_first_run(self) -> bool:
        return not self._users.has_any()

    def create_initial_admin(self, login: str = "admin", password: str = "admin1234") -> int:
        user_id = self._users.create(login=login, password_hash=hash_password(password), role="admin")
        self._audit.log(AuditEvent(user_id, login, "users", str(user_id), "create_initial_admin", {}))
        return user_id

    def create_user(self, payload: UserCreateIn, actor: SessionContext) -> int:
        if actor.role != "admin":
            raise PermissionError("Only admin can create users.")
        user_id = self._users.create(
            login=payload.login.strip(),
            password_hash=hash_password(payload.password),
            role=payload.role,
        )
        self._audit.log(
            AuditEvent(actor.user_id, actor.login, "users", str(user_id), "create", {"role": payload.role})
        )
        return user_id

    def set_user_active(self, user_id: int, is_active: bool, actor: SessionContext) -> bool:
        if actor.role != "admin":
            raise PermissionError("Only admin can update users.")
        ok = self._users.set_active(user_id, is_active)
        if ok:
            self._audit.log(
                AuditEvent(
                    actor.user_id,
                    actor.login,
                    "users",
                    str(user_id),
                    "activate" if is_active else "deactivate",
                    {},
                )
            )
        return ok

    def reset_password(self, user_id: int, new_password: str, actor: SessionContext) -> bool:
        if actor.role != "admin":
            raise PermissionError("Only admin can reset passwords.")
        ok = self._users.set_password_hash(user_id, hash_password(new_password))
        if ok:
            self._audit.log(AuditEvent(actor.user_id, actor.login, "users", str(user_id), "reset_password", {}))
        return ok

    def login(self, login: str, password: str) -> SessionContext | None:
        login = login.strip()
        locked, _ = self.is_locked(login)
        if locked:
            return None
        user = self._users.get_by_login(login)
        if not user or not user.is_active:
            self.record_failure(login)
            return None
        if not verify_password(password, user.password_hash):
            self.record_failure(login)
            return None
        session = SessionContext(user_id=user.id, login=user.login, role=user.role)
        self._audit.log(AuditEvent(session.user_id, session.login, "users", str(session.user_id), "login", {}))
        return session

    def login_dto(self, login: str, password: str) -> SessionOut | None:
        session = self.login(login, password)
        if session is None:
            return None
        return SessionOut(user_id=session.user_id, login=session.login, role=session.role)

    def list_users(self):
        return self._users.list_users()
