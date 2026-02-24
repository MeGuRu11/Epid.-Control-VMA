from __future__ import annotations

from PySide6.QtWidgets import QWidget

from app.ui.widgets.toast import ToastManager


def test_toast_manager_adds_and_positions_toast(qapp) -> None:
    parent = QWidget()
    parent.resize(800, 600)
    manager = ToastManager(parent)

    toast = manager.show("ok", level="info", timeout_ms=5000)
    qapp.processEvents()

    assert toast in manager.toasts
    assert toast.x() >= 0
    assert toast.y() >= 0


def test_toast_manager_repositions_on_parent_resize(qapp) -> None:
    parent = QWidget()
    parent.resize(700, 500)
    parent.show()
    manager = ToastManager(parent)

    toast = manager.show("resize", level="success", timeout_ms=5000)
    qapp.processEvents()
    before_x = toast.x()
    parent.resize(900, 500)
    manager._layout_toasts()
    qapp.processEvents()

    assert toast.x() > before_x
