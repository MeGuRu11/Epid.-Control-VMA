from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget


class EmptyState(QWidget):
    """Плашка «нет данных» для вкладок Analytics v2."""

    def __init__(
        self,
        message: str = "Нет данных за выбранный период.",
        hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        frame = QFrame()
        frame.setObjectName("emptyState")

        msg_label = QLabel(message)
        msg_label.setObjectName("emptyStateText")
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_label.setWordWrap(True)

        inner = QVBoxLayout(frame)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(msg_label)

        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("emptyStateHint")
            hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint_label.setWordWrap(True)
            inner.addWidget(hint_label)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 16, 0, 16)
        root.addWidget(frame)


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
