from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedLayout, QStackedWidget, QWidget


class TransitionStack(QStackedWidget):
    def __init__(self, parent: QWidget | None = None, *, animations_enabled: bool = True) -> None:
        super().__init__(parent)
        self._animations_enabled = animations_enabled
        self._busy = False
        self._queued: tuple[QWidget, int] | None = None
        self._fade: QPropertyAnimation | None = None

        layout = self.layout()
        if isinstance(layout, QStackedLayout):
            layout.setStackingMode(QStackedLayout.StackingMode.StackOne)

    def set_animations_enabled(self, enabled: bool) -> None:
        self._animations_enabled = enabled

    def setCurrentWidgetAnimated(self, widget: QWidget, direction: int = 1) -> None:  # noqa: N802
        _ = direction
        if widget is self.currentWidget():
            return
        if not self._animations_enabled:
            self.setCurrentWidget(widget)
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
                page.setGraphicsEffect(None)  # type: ignore[arg-type]
        if current.graphicsEffect() is not None:
            current.setGraphicsEffect(None)  # type: ignore[arg-type]

        self._busy = False
        queued = self._queued
        self._queued = None
        if queued:
            QTimer.singleShot(0, lambda: self.setCurrentWidgetAnimated(*queued))
