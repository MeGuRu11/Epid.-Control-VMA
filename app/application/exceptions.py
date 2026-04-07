from __future__ import annotations


class AppError(Exception):
    def __init__(self, message: str = "", *, original: Exception | None = None) -> None:
        super().__init__(message)
        self.original = original


class DatabaseError(AppError):
    """Ошибка при работе с БД."""


class AuthenticationError(AppError):
    """Ошибка аутентификации."""


class PermissionError(AppError):  # noqa: A001
    """Недостаточно прав."""
