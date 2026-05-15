from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget


class TrendIndicator(QLabel):
    """Показывает изменение KPI относительно предыдущего периода."""

    def __init__(
        self,
        metric_kind: str = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._metric_kind = metric_kind
        self.setObjectName("kpiTrendFlat")
        self.setText("—")

    def set_change(self, current: float | int, previous: float | int | None) -> None:
        if previous is None or previous == 0:
            self._set("—", "kpiTrendFlat")
            return

        pct = (current - previous) / abs(previous) * 100
        if abs(pct) < 0.5:
            self._set("—", "kpiTrendFlat")
            return

        growing = pct > 0
        arrow = "▲" if growing else "▼"
        text = f"{arrow} {abs(pct):.1f}%"

        if self._metric_kind == "neutral":
            name = "kpiTrendFlat"
        elif self._metric_kind == "positive":
            name = "kpiTrendUp" if growing else "kpiTrendDown"
        else:
            name = "kpiTrendDown" if growing else "kpiTrendUp"

        self._set(text, name)

    def clear_trend(self) -> None:
        self._set("—", "kpiTrendFlat")

    def _set(self, text: str, obj_name: str) -> None:
        self.setText(text)
        self.setObjectName(obj_name)
        self.style().unpolish(self)
        self.style().polish(self)
