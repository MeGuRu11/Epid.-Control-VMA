from __future__ import annotations

from typing import cast

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QPushButton, QWidget


def disable_enter_defaults(root: QWidget) -> None:
    buttons = cast(list[QPushButton], root.findChildren(QPushButton))
    for button in buttons:
        button.setAutoDefault(False)
        button.setDefault(False)


def install_enter_key_guard(root: QWidget, owner: QObject) -> None:
    root.installEventFilter(owner)
    children = cast(list[QWidget], root.findChildren(QWidget))
    for child in children:
        child.installEventFilter(owner)


def is_enter_key_press(event: QEvent) -> bool:
    if event.type() != QEvent.Type.KeyPress:
        return False
    if not isinstance(event, QKeyEvent):
        return False
    return event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
