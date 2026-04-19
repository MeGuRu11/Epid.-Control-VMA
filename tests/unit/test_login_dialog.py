from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from app.application.services.auth_service import AuthService
from app.ui.login_dialog import LoginDialog


def test_login_dialog_keeps_windowed_geometry_within_available_screen(qapp) -> None:
    dialog = LoginDialog(auth_service=cast(AuthService, SimpleNamespace()))
    screen = dialog.screen() or qapp.primaryScreen()

    assert screen is not None

    geometry = screen.availableGeometry()

    assert dialog.minimumWidth() < geometry.width()
    assert dialog.minimumHeight() < geometry.height()
    assert dialog.width() < geometry.width()
    assert dialog.height() < geometry.height()
