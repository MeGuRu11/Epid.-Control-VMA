from __future__ import annotations

from weakref import WeakKeyDictionary

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QWidget,
)

_VALID_LEVELS = {"success", "warning", "error", "info"}


def _effects_supported() -> bool:
    """Вернуть True если платформа поддерживает тени и анимацию opacity.

    На Windows с offscreen-платформой QGraphicsDropShadowEffect и
    QPropertyAnimation(windowOpacity) вызывают access violation, потому что
    offscreen backend не инициализирует нативные оконные дескрипторы.
    Проверяем через переменную окружения — самый надёжный способ.
    """
    import os

    return os.environ.get("QT_QPA_PLATFORM", "").lower() not in ("offscreen", "minimal")


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
        self._toast_text = text
        self._toast_level = level if level in _VALID_LEVELS else "info"
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("toast")
        self.setProperty("toastLevel", self._toast_level)
        self.setMaximumWidth(460)

        if _effects_supported():
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(28)
            shadow.setOffset(0, 8)
            shadow.setColor(QColor(54, 46, 38, 55))
            self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setMaximumWidth(420)
        layout.addWidget(label)

        if _effects_supported():
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
        else:
            # Headless / offscreen: без анимации, авто-закрытие через таймер.
            self._anim_in = None  # type: ignore[assignment]
            self._anim_out = None  # type: ignore[assignment]
            self.setWindowOpacity(1.0)
            QTimer.singleShot(timeout_ms, self._finalize_close)

    def matches(self, *, text: str, level: str) -> bool:
        normalized_level = level if level in _VALID_LEVELS else "info"
        return self._toast_text == text and self._toast_level == normalized_level

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
        for existing in list(self.toasts):
            if existing.matches(text=text, level=level):
                existing._manager = None
                self.toasts.remove(existing)
                existing.hide()
                existing.deleteLater()
        toast = Toast(self.parent_widget, text=text, level=level, timeout_ms=timeout_ms)
        toast._manager = self
        self.toasts.append(toast)
        self._layout_toasts()
        toast.show()
        toast.raise_()
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
        margin = 20
        spacing = 10
        top_offset = 44
        parent_width = self.parent_widget.width()
        y = margin + top_offset
        for toast in self.toasts:
            toast.adjustSize()
            x = max(margin, parent_width - toast.width() - margin)
            toast.move(x, y)
            toast.raise_()
            y += toast.height() + spacing


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

