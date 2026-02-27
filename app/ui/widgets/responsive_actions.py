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
        self._compact_override: bool | None = None
        self._compact = False
        self._compact_active = False

        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(6)
        self._grid.setVerticalSpacing(4)

    def set_compact(self, compact: bool | None) -> None:
        # `None` returns the panel to fully automatic compact mode.
        self._compact_override = compact
        self._reflow()

    def add_button(self, button: QPushButton) -> None:
        self._buttons.append(button)
        self._reflow()

    def set_buttons(self, buttons: list[QPushButton]) -> None:
        self._buttons = list(buttons)
        self._reflow()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reflow()

    def is_compact(self) -> bool:
        return self._compact_active

    def _resolve_compact(self, button_count: int) -> bool:
        if self._compact_override is not None:
            return self._compact_override
        if button_count <= 0:
            return False
        columns = min(self._max_columns, button_count)
        regular_spacing = 6
        needed = columns * self._min_button_width + max(0, columns - 1) * regular_spacing
        margins = self._grid.contentsMargins()
        needed += margins.left() + margins.right()
        return self.width() < needed

    def _columns_for_width(self, *, min_button_width: int, spacing: int, button_count: int) -> int:
        if button_count <= 0:
            return 1
        margins = self._grid.contentsMargins()
        available = max(1, self.width() - margins.left() - margins.right())
        cell = min_button_width + max(0, spacing)
        by_width = max(1, available // max(1, cell))
        return max(1, min(self._max_columns, min(button_count, by_width)))

    def _tune_button(self, button: QPushButton, *, compact: bool) -> None:
        button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        min_width = 96 if compact else self._min_button_width
        if button.minimumWidth() != min_width:
            button.setMinimumWidth(min_width)

    def _apply_compact_mode(self, compact: bool) -> tuple[int, int, int]:
        h_spacing = 4 if compact else 6
        v_spacing = 3 if compact else 4
        min_width = 96 if compact else self._min_button_width
        if self._grid.horizontalSpacing() != h_spacing:
            self._grid.setHorizontalSpacing(h_spacing)
        if self._grid.verticalSpacing() != v_spacing:
            self._grid.setVerticalSpacing(v_spacing)
        for button in self._buttons:
            self._tune_button(button, compact=compact)
        self._compact = compact
        self._compact_active = compact
        return min_width, h_spacing, v_spacing

    def _clear_layout(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(self)

    def _reflow(self) -> None:
        visible_buttons = [button for button in self._buttons if button.isVisible()]
        compact = self._resolve_compact(len(visible_buttons))
        min_width, h_spacing, _v_spacing = self._apply_compact_mode(compact)

        self._clear_layout()
        if not visible_buttons:
            return
        columns = self._columns_for_width(
            min_button_width=min_width,
            spacing=h_spacing,
            button_count=len(visible_buttons),
        )
        for idx, button in enumerate(visible_buttons):
            row = idx // columns
            col = idx % columns
            self._grid.addWidget(button, row, col, alignment=Qt.AlignmentFlag.AlignHCenter)
