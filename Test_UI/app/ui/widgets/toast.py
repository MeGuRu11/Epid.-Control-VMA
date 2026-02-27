from __future__ import annotations

from weakref import WeakKeyDictionary

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ..style import COL


class Toast(QWidget):
    def __init__(self, parent: QWidget, text: str, kind: str = "info", timeout_ms: int = 2400):
        super().__init__(parent)
        self._manager: ToastManager | None = None
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)

        bg = {
            "success": COL["success_bg"],
            "warning": COL["warn_bg"],
            "error": COL["error_bg"],
            "info": COL["info_bg"],
        }.get(kind, COL["info_bg"])
        border = {
            "success": COL["success"],
            "warning": COL["warn"],
            "error": COL["error"],
            "info": "#C9C6C1",
        }.get(kind, "#C9C6C1")

        self.setStyleSheet(
            f"""
            Toast {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setMaximumWidth(420)
        layout.addWidget(label)

        self._anim_in = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim_in.setDuration(180)
        self._anim_in.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_in.setStartValue(0.0)
        self._anim_in.setEndValue(1.0)

        self._anim_out = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim_out.setDuration(180)
        self._anim_out.setEasingCurve(QEasingCurve.InCubic)
        self._anim_out.setStartValue(1.0)
        self._anim_out.setEndValue(0.0)
        self._anim_out.finished.connect(self._finalize_close)

        self.setWindowOpacity(0.0)
        self._anim_in.start()
        QTimer.singleShot(timeout_ms, self._anim_out.start)

    def _finalize_close(self) -> None:
        manager = self._manager
        if manager:
            manager.detach(self)
        self.deleteLater()


class ToastManager(QObject):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.parent_widget = parent
        self.toasts: list[Toast] = []
        self.parent_widget.installEventFilter(self)

    def show(self, text: str, kind: str = "info", timeout_ms: int = 2400) -> Toast:
        toast = Toast(self.parent_widget, text=text, kind=kind, timeout_ms=timeout_ms)
        toast._manager = self
        self.toasts.append(toast)
        self._layout_toasts()
        toast.show()
        return toast

    def detach(self, toast: Toast) -> None:
        if toast in self.toasts:
            self.toasts.remove(toast)
            self._layout_toasts()

    def eventFilter(self, watched, event):
        if watched is self.parent_widget and event.type() in (QEvent.Resize, QEvent.Move):
            self._layout_toasts()
        return super().eventFilter(watched, event)

    def _layout_toasts(self) -> None:
        margin = 16
        spacing = 8
        parent_width = self.parent_widget.width()
        parent_height = self.parent_widget.height()
        y = parent_height - margin
        for toast in reversed(self.toasts):
            toast.adjustSize()
            x = max(margin, parent_width - toast.width() - margin)
            y -= toast.height()
            toast.move(x, y)
            y -= spacing


_MANAGERS: "WeakKeyDictionary[QWidget, ToastManager]" = WeakKeyDictionary()


def show_toast(parent, text: str, kind: str = "info"):
    host = parent.window() if parent is not None else None
    if host is None:
        host = parent
    if host is None:
        return None

    manager = _MANAGERS.get(host)
    if manager is None:
        manager = ToastManager(host)
        _MANAGERS[host] = manager
    return manager.show(text=text, kind=kind)
