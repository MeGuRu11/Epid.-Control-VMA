from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Signal
from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout, QWidget


class SidebarDrawer(QWidget):
    pageRequested = Signal(str)

    def __init__(self):
        super().__init__()
        self._expanded_w = 266
        self._collapsed_w = 92
        self._collapsed = False
        self._current_key: str | None = None

        self.setMinimumWidth(self._expanded_w)
        self.setMaximumWidth(self._expanded_w)

        self._anim_min = QPropertyAnimation(self, b"minimumWidth", self)
        self._anim_max = QPropertyAnimation(self, b"maximumWidth", self)
        for anim in (self._anim_min, self._anim_max):
            anim.setDuration(220)
            anim.setEasingCurve(QEasingCurve.OutCubic)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame()
        self.card.setObjectName("sidebar")
        outer.addWidget(self.card)

        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(10, 12, 10, 12)
        lay.setSpacing(8)

        self.btn_toggle = QPushButton("◀ Меню")
        self.btn_toggle.setObjectName("ghost")
        self.btn_toggle.clicked.connect(self.toggle)
        lay.addWidget(self.btn_toggle)

        # key, short label, icon marker, full label
        self.nav_items: list[tuple[str, str, str, str]] = [
            ("home", "HM", "⌂", "Главная"),
            ("emr", "EM", "✚", "ЭМЗ"),
            ("form100", "F100", "F", "Форма 100"),
            ("patient", "PT", "☰", "Поиск и ЭМК"),
            ("lab", "LAB", "⚗", "Лаборатория"),
            ("sanitary", "SAN", "⛨", "Санитария"),
            ("analytics", "AN", "◔", "Аналитика"),
            ("import_export", "IMP", "⇄", "Импорт/Экспорт"),
            ("references", "REF", "☷", "Справочники"),
            ("admin", "ADM", "⚙", "Администрирование"),
        ]

        self._buttons: dict[str, QPushButton] = {}
        for key, _, _, _ in self.nav_items:
            button = QPushButton()
            button.setObjectName("navButton")
            button.setProperty("active", False)
            button.clicked.connect(lambda checked=False, k=key: self.pageRequested.emit(k))
            lay.addWidget(button)
            self._buttons[key] = button

        lay.addStretch(1)
        self._sync_texts()

    def toggle(self):
        self._collapsed = not self._collapsed
        end = self._collapsed_w if self._collapsed else self._expanded_w

        self._sync_texts()
        self._anim_min.stop()
        self._anim_max.stop()
        self._anim_min.setStartValue(self.minimumWidth())
        self._anim_min.setEndValue(end)
        self._anim_max.setStartValue(self.maximumWidth())
        self._anim_max.setEndValue(end)
        self._anim_min.start()
        self._anim_max.start()

    def set_visible_for_role(self, role: str):
        self._buttons["admin"].setVisible(role == "admin")

    def set_current_page(self, key: str):
        if self._current_key == key:
            return
        self._current_key = key
        for page_key, button in self._buttons.items():
            button.setProperty("active", page_key == key)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def _sync_texts(self):
        self.btn_toggle.setText("▶" if self._collapsed else "◀ Меню")
        for key, short_label, icon, full_label in self.nav_items:
            button = self._buttons[key]
            button.setText(short_label if self._collapsed else f"{icon}  {full_label}")
            button.setToolTip(full_label if self._collapsed else "")

