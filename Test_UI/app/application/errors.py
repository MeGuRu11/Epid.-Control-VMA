from __future__ import annotations


class AppError(RuntimeError):
    """Base application-level error."""


class ValidationError(AppError):
    """Input validation failure."""


class AccessDeniedError(AppError):
    """RBAC/permission failure."""

