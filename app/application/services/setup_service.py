from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select

from app.infrastructure.db.models_sqlalchemy import User
from app.infrastructure.db.session import session_scope
from app.infrastructure.security.password_hash import hash_password


class SetupService:
    """Сервис первичной настройки приложения."""

    def __init__(self, session_factory: Callable = session_scope) -> None:
        self.session_factory = session_factory

    def create_initial_user(self, *, login: str, password: str) -> None:
        """Создаёт первого администратора при первичном запуске приложения."""
        normalized_login = login.strip()
        if not normalized_login:
            raise ValueError("Введите логин администратора.")
        if not password:
            raise ValueError("Введите пароль.")

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
