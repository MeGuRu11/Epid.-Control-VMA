from __future__ import annotations

from typing import Final, Literal

Role = Literal["admin", "operator"]
Permission = Literal[
    "access_admin_view",
    "manage_users",
    "manage_references",
    "manage_backups",
]

_ROLE_PERMISSIONS: Final[dict[Role, frozenset[Permission]]] = {
    "admin": frozenset(
        {
            "access_admin_view",
            "manage_users",
            "manage_references",
            "manage_backups",
        }
    ),
    "operator": frozenset(),
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in _ROLE_PERMISSIONS[role]


def can_access_admin_view(role: Role) -> bool:
    return has_permission(role, "access_admin_view")


def can_manage_users(role: Role) -> bool:
    return has_permission(role, "manage_users")


def can_manage_references(role: Role) -> bool:
    return has_permission(role, "manage_references")


def can_manage_backups(role: Role) -> bool:
    return has_permission(role, "manage_backups")
