from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QPushButton, QSizePolicy, QWidget


class ResponsiveActionsPanel(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        min_button_width: int = 112,
        max_columns: int = 6,
    ) -> None:
        super().__init__(parent)
        self._buttons: list[QPushButton] = []
        self._min_button_width = min_button_width
        self._max_columns = max_columns
        self._compact = False

        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(6)
        self._grid.setVerticalSpacing(4)

    def set_compact(self, compact: bool) -> None:
        self._compact = compact
        self._grid.setHorizontalSpacing(4 if compact else 6)
        self._grid.setVerticalSpacing(3 if compact else 4)
        for button in self._buttons:
            self._tune_button(button)
        self._reflow()

    def add_button(self, button: QPushButton) -> None:
        self._buttons.append(button)
        self._tune_button(button)
        self._reflow()

    def set_buttons(self, buttons: list[QPushButton]) -> None:
        self._buttons = list(buttons)
        for button in self._buttons:
            self._tune_button(button)
        self._reflow()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reflow()

    def _columns_for_width(self) -> int:
        width = max(1, self.width())
        spacing = self._grid.horizontalSpacing()
        cell = self._min_button_width + max(0, spacing)
        return max(1, min(self._max_columns, width // max(1, cell)))

    def _tune_button(self, button: QPushButton) -> None:
        button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        min_width = 96 if self._compact else self._min_button_width
        button.setMinimumWidth(min_width)

    def _clear_layout(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(self)

    def _reflow(self) -> None:
        self._clear_layout()
        if not self._buttons:
            return
        columns = self._columns_for_width()
        for idx, button in enumerate(self._buttons):
            row = idx // columns
            col = idx % columns
            self._grid.addWidget(button, row, col, alignment=Qt.AlignmentFlag.AlignHCenter)
