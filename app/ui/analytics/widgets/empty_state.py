from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QResizeEvent, QShowEvent
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget


class EmptyState(QWidget):
    """Плашка «нет данных» для вкладок Analytics v2."""

    _BASE_MIN_HEIGHT = 132

    def __init__(
        self,
        message: str = "Нет данных за выбранный период.",
        hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._wrapped_labels: list[QLabel] = []
        self._refreshing_geometry = False
        self.setMinimumHeight(self._BASE_MIN_HEIGHT)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
        )
        frame = QFrame()
        self._frame = frame
        frame.setObjectName("emptyState")
        frame.setMinimumHeight(self._BASE_MIN_HEIGHT)
        frame.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
        )

        msg_label = QLabel(message)
        msg_label.setObjectName("emptyStateText")
        self._configure_wrapped_label(msg_label)

        inner = QVBoxLayout(frame)
        self._inner_layout = inner
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(msg_label)

        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("emptyStateHint")
            self._configure_wrapped_label(hint_label)
            inner.addWidget(hint_label)

        root = QVBoxLayout(self)
        self._root_layout = root
        root.setContentsMargins(0, 16, 0, 16)
        root.addWidget(frame)
        self._refresh_wrapped_label_geometry()

    def event(self, event: QEvent) -> bool:
        result = super().event(event)
        if event.type() == QEvent.Type.LayoutRequest:
            self._refresh_wrapped_label_geometry()
        return result

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._refresh_wrapped_label_geometry()

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self._refresh_wrapped_label_geometry()

    def _configure_wrapped_label(self, label: QLabel) -> None:
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        policy.setHeightForWidth(True)
        label.setSizePolicy(policy)
        self._wrapped_labels.append(label)

    def _refresh_wrapped_label_geometry(self) -> None:
        if self._refreshing_geometry:
            return
        self._refreshing_geometry = True
        try:
            changed = False
            for label in self._wrapped_labels:
                width = label.width()
                if width <= 0:
                    margins = self._root_layout.contentsMargins()
                    width = max(1, self.width() - margins.left() - margins.right())
                needed = label.heightForWidth(width)
                if needed < 0:
                    needed = label.sizeHint().height()
                needed = max(needed, label.sizeHint().height(), label.minimumSizeHint().height())
                if label.minimumHeight() != needed:
                    label.setMinimumHeight(needed)
                    changed = True

            frame_minimum = max(self._BASE_MIN_HEIGHT, self._inner_layout.sizeHint().height())
            if self._frame.minimumHeight() != frame_minimum:
                self._frame.setMinimumHeight(frame_minimum)
                changed = True

            widget_minimum = max(self._BASE_MIN_HEIGHT, self._root_layout.sizeHint().height())
            if self.minimumHeight() != widget_minimum:
                self.setMinimumHeight(widget_minimum)
                changed = True
            if self.height() < widget_minimum:
                self.resize(self.width(), widget_minimum)
            if changed:
                self.updateGeometry()
        finally:
            self._refreshing_geometry = False


def make_inline_placeholder(message: str) -> QLabel:
    """Компактный inline-плейсхолдер для пустых графиков/таблиц внутри секций."""
    label = QLabel(message)
    label.setObjectName("inlinePlaceholder")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setWordWrap(True)
    label.setMinimumHeight(80)
    label.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.MinimumExpanding,
    )
    return label


class CurrentWidgetStack(QStackedWidget):
    """Stack для inline-секций, размер которого определяется текущей страницей."""

    def sizeHint(self) -> QSize:  # noqa: N802
        current = self.currentWidget()
        if current is None:
            return super().sizeHint()
        return current.sizeHint().expandedTo(current.minimumSize())

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        current = self.currentWidget()
        if current is None:
            return super().minimumSizeHint()
        hint = current.minimumSizeHint()
        if not hint.isValid():
            hint = QSize(0, 0)
        return hint.expandedTo(current.minimumSize())

    def _refresh_geometry(self) -> None:
        current = self.currentWidget()
        if current is not None:
            current.updateGeometry()
        self.updateGeometry()
        parent = self.parentWidget()
        if parent is not None:
            layout = parent.layout()
            if layout is not None:
                layout.invalidate()
                layout.activate()
            parent.updateGeometry()

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        super().setCurrentIndex(index)
        self._refresh_geometry()

    def setCurrentWidget(self, widget: QWidget) -> None:  # noqa: N802
        super().setCurrentWidget(widget)
        self._refresh_geometry()
