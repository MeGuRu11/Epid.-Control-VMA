from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from PySide6.QtCore import QPoint, QRect, QSize

from app.main import (
    _apply_initial_window_size,
    _compute_initial_window_size,
    _resolve_initial_screen,
)


@dataclass
class _DummyScreen:
    geometry: QRect

    def availableGeometry(self) -> QRect:  # noqa: N802
        return self.geometry


@dataclass
class _DummyHandle:
    current_screen: _DummyScreen | None

    def screen(self) -> _DummyScreen | None:
        return self.current_screen


class _DummyWindow:
    def __init__(
        self,
        *,
        handle_screen: _DummyScreen | None = None,
        fallback_screen: _DummyScreen | None = None,
        minimum_size: QSize | None = None,
    ) -> None:
        self._handle = _DummyHandle(handle_screen) if handle_screen is not None else None
        self._screen = fallback_screen
        self._minimum_size = minimum_size or QSize(640, 480)
        self.resized_to: tuple[int, int] | None = None
        self.moved_to: tuple[int, int] | None = None

    def windowHandle(self) -> _DummyHandle | None:  # noqa: N802
        return self._handle

    def screen(self) -> _DummyScreen | None:
        return self._screen

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return self._minimum_size

    def resize(self, width: int, height: int) -> None:
        self.resized_to = (width, height)

    def move(self, x: int, y: int) -> None:
        self.moved_to = (x, y)


class _DummyApp:
    def __init__(
        self,
        *,
        cursor_screen: _DummyScreen | None = None,
        primary_screen: _DummyScreen | None = None,
    ) -> None:
        self._cursor_screen = cursor_screen
        self._primary_screen = primary_screen

    def screenAt(self, _point: QPoint) -> _DummyScreen | None:  # noqa: N802
        return self._cursor_screen

    def primaryScreen(self) -> _DummyScreen | None:  # noqa: N802
        return self._primary_screen


def test_resolve_initial_screen_prefers_window_handle_screen(monkeypatch) -> None:
    handle_screen = _DummyScreen(QRect(100, 50, 1600, 900))
    cursor_screen = _DummyScreen(QRect(0, 0, 1920, 1009))
    primary_screen = _DummyScreen(QRect(0, 0, 2560, 1369))
    window = _DummyWindow(handle_screen=handle_screen, fallback_screen=primary_screen)
    app = _DummyApp(cursor_screen=cursor_screen, primary_screen=primary_screen)

    monkeypatch.setattr("app.main.QCursor.pos", lambda: QPoint(400, 300))

    assert _resolve_initial_screen(cast(Any, window), cast(Any, app)) is handle_screen


def test_compute_initial_window_size_clamps_to_available_geometry() -> None:
    width, height = _compute_initial_window_size(QRect(0, 0, 1920, 1009), QSize(846, 1167))

    assert width == 1766
    assert height == 1009


def test_apply_initial_window_size_centers_window_on_resolved_screen(monkeypatch) -> None:
    screen = _DummyScreen(QRect(100, 20, 1600, 900))
    window = _DummyWindow(handle_screen=screen, minimum_size=QSize(640, 480))
    app = _DummyApp(primary_screen=screen)

    monkeypatch.setattr("app.main.QCursor.pos", lambda: QPoint(200, 100))

    _apply_initial_window_size(cast(Any, window), cast(Any, app))

    assert window.resized_to == (1472, 810)
    assert window.moved_to == (164, 65)
