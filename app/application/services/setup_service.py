from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select

from app.infrastructure.db.models_sqlalchemy import User
from app.infrastructure.db.session import session_scope
from app.infrastructure.security.password_hash import hash_password

MIN_PASSWORD_LENGTH = 8


class SetupService:
    """Сервис первичной настройки приложения."""

    def __init__(self, session_factory: Callable = session_scope) -> None:
        self.session_factory = session_factory

    def create_initial_user(self, *, login: str, password: str) -> None:
        """Создаёт первого администратора при первом запуске приложения."""
        normalized_login = login.strip()
        if not normalized_login:
            raise ValueError("Введите логин администратора.")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Пароль должен быть не менее {MIN_PASSWORD_LENGTH} символов.")

        with self.session_factory() as session:
            exists = session.execute(select(User.id).where(User.login == normalized_login)).first()
            if exists:
                raise ValueError("Логин уже существует. Выберите другой.")
            session.add(
                User(
                    login=normalized_login,
                    password_hash=hash_password(password),
                    role="admin",
                    is_active=True,
                )
            )
