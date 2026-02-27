from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedLayout, QStackedWidget, QWidget


class TransitionStack(QStackedWidget):
    """Safe page transitions without page layer overlap."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._busy = False
        self._queued: tuple[QWidget, int] | None = None
        self._fade: QPropertyAnimation | None = None

        layout = self.layout()
        if isinstance(layout, QStackedLayout):
            layout.setStackingMode(QStackedLayout.StackingMode.StackOne)

    def setCurrentWidgetAnimated(self, widget: QWidget, direction: int = 1):
        _ = direction
        if widget is self.currentWidget():
            return
        if self._busy:
            self._queued = (widget, direction)
            return

        self._busy = True
        self._queued = None

        self.setCurrentWidget(widget)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.0)

        self._fade = QPropertyAnimation(effect, b"opacity", self)
        self._fade.setDuration(160)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.finished.connect(lambda: self._finish_transition(widget))
        self._fade.start()

    def _ensure_opacity_effect(self, widget: QWidget) -> QGraphicsOpacityEffect:
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        return effect

    def _finish_transition(self, current: QWidget) -> None:
        for idx in range(self.count()):
            page = self.widget(idx)
            if page is not None and page is not current and page.graphicsEffect() is not None:
                page.setGraphicsEffect(None)
        if current.graphicsEffect() is not None:
            current.setGraphicsEffect(None)

        self._busy = False
        queued = self._queued
        self._queued = None
        if queued:
            QTimer.singleShot(0, lambda: self.setCurrentWidgetAnimated(*queued))
