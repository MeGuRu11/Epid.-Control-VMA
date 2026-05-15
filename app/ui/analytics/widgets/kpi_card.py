from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.analytics.widgets.trend_indicator import TrendIndicator


class KpiCard(QFrame):
    """KPI-карточка для обзорной вкладки аналитики."""

    clicked = Signal()

    def __init__(
        self,
        title: str,
        icon_symbol: str,
        icon_category: str = "neutral",
        metric_kind: str = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._icon = QLabel(icon_symbol)
        self._icon.setObjectName("kpiIcon")
        self._icon.setProperty("iconCategory", icon_category)
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setFixedSize(40, 40)

        self._title = QLabel(title.upper())
        self._title.setObjectName("kpiTitle")

        self._value = QLabel("—")
        self._value.setObjectName("kpiValue")

        self._trend = TrendIndicator(metric_kind=metric_kind)

        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(8)
        value_row.addWidget(self._value, 1)
        value_row.addWidget(self._trend, 0)

        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(6)
        body.addWidget(self._title)
        body.addLayout(value_row)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)
        root.addWidget(self._icon)
        root.addLayout(body, 1)

    def set_value(self, text: str) -> None:
        self._value.setText(text)

    def set_trend(self, current: float | int, previous: float | int | None) -> None:
        self._trend.set_change(current, previous)

    def clear_trend(self) -> None:
        self._trend.clear_trend()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        super().mousePressEvent(event)
        self.clicked.emit()
