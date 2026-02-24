from __future__ import annotations

from weakref import WeakKeyDictionary

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

_VALID_LEVELS = {"success", "warning", "error", "info"}


class Toast(QWidget):
    def __init__(
        self,
        parent: QWidget,
        text: str,
        *,
        level: str = "info",
        timeout_ms: int = 2400,
    ) -> None:
        super().__init__(parent)
        self._manager: ToastManager | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("toast")
        self.setProperty("toastLevel", level if level in _VALID_LEVELS else "info")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setMaximumWidth(420)
        layout.addWidget(label)

        self._anim_in = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim_in.setDuration(180)
        self._anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_in.setStartValue(0.0)
        self._anim_in.setEndValue(1.0)

        self._anim_out = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim_out.setDuration(180)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
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
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.parent_widget = parent
        self.toasts: list[Toast] = []
        self.parent_widget.installEventFilter(self)

    def show(self, text: str, *, level: str = "info", timeout_ms: int = 2400) -> Toast:
        toast = Toast(self.parent_widget, text=text, level=level, timeout_ms=timeout_ms)
        toast._manager = self
        self.toasts.append(toast)
        self._layout_toasts()
        toast.show()
        return toast

    def detach(self, toast: Toast) -> None:
        if toast in self.toasts:
            self.toasts.remove(toast)
            self._layout_toasts()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        parent_widget = getattr(self, "parent_widget", None)
        if parent_widget is None:
            return False
        if watched is parent_widget and event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
            self._layout_toasts()
        return super().eventFilter(watched, event)

    def _layout_toasts(self) -> None:
        if not hasattr(self, "parent_widget"):
            return
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


_MANAGERS: WeakKeyDictionary[QWidget, ToastManager] = WeakKeyDictionary()


def show_toast(parent: QWidget | None, text: str, level: str = "info") -> Toast | None:
    host = parent.window() if parent is not None else None
    if host is None:
        host = parent
    if host is None:
        return None

    manager = _MANAGERS.get(host)
    if manager is None:
        manager = ToastManager(host)
        _MANAGERS[host] = manager
    return manager.show(text=text, level=level)
