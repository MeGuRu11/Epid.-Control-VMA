from __future__ import annotations

from app.application.security import (
    can_access_admin_view,
    can_manage_backups,
    can_manage_references,
    can_manage_users,
    has_permission,
)


def test_admin_has_all_declared_permissions() -> None:
    assert can_access_admin_view("admin") is True
    assert can_manage_users("admin") is True
    assert can_manage_references("admin") is True
    assert can_manage_backups("admin") is True
    assert has_permission("admin", "manage_references") is True


def test_operator_has_read_only_scope_for_admin_features() -> None:
    assert can_access_admin_view("operator") is False
    assert can_manage_users("operator") is False
    assert can_manage_references("operator") is False
    assert can_manage_backups("operator") is False
    assert has_permission("operator", "manage_users") is False
