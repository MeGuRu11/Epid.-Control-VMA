from __future__ import annotations

from datetime import date, datetime
from typing import cast

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.services.reference_service import ReferenceService
from app.application.services.sanitary_service import SanitaryService
from app.ui.sanitary.sanitary_history import SanitaryHistoryDialog
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.responsive_actions import ResponsiveActionsPanel


class SanitaryDashboard(QWidget):
    references_updated = Signal()

    def __init__(
        self,
        sanitary_service: SanitaryService,
        reference_service: ReferenceService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.sanitary_service = sanitary_service
        self.reference_service = reference_service
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        title_row = QHBoxLayout()
        title = QLabel("Санитарная микробиология - отделения")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        self.summary_label = QLabel("Отделений: 0, проб: 0, положительных: 0")
        self.summary_label.setObjectName("muted")
        title_row.addWidget(self.summary_label)
        layout.addLayout(title_row)

        quick_open = QPushButton("Открыть историю отделения")
        compact_button(quick_open)
        quick_open.clicked.connect(self._open_selected)
        quick_refresh = QPushButton("Обновить")
        compact_button(quick_refresh)
        quick_refresh.clicked.connect(self.refresh)
        self._quick_actions_panel = ResponsiveActionsPanel(min_button_width=146, max_columns=2)
        self._quick_actions_panel.set_buttons([quick_open, quick_refresh])
        self._quick_actions_panel.set_compact(self.width() < 1340)
        layout.addWidget(self._quick_actions_panel)

        filter_box = QGroupBox("Фильтры")
        filter_row = QHBoxLayout(filter_box)
        self.filter_enabled = QCheckBox("Фильтр по дате")
        self.filter_enabled.setChecked(False)
        self.filter_enabled.stateChanged.connect(self.refresh)
        min_date = QDate(2024, 1, 1)
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setMinimumDate(min_date)
        self.date_from.dateChanged.connect(self.refresh)
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setMinimumDate(min_date)
        self.date_to.dateChanged.connect(self.refresh)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по отделению")
        self.search_input.textChanged.connect(self.refresh)
        self.growth_filter = QComboBox()
        self.growth_filter.addItem("Рост: все", None)
        self.growth_filter.addItem("Рост: положительные", 1)
        self.growth_filter.addItem("Рост: отрицательные", 0)
        self.growth_filter.addItem("Рост: не указан", -1)
        self.growth_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.filter_enabled)
        filter_row.addWidget(QLabel("с"))
        filter_row.addWidget(self.date_from)
        filter_row.addWidget(QLabel("по"))
        filter_row.addWidget(self.date_to)
        filter_row.addWidget(QLabel("Поиск"))
        filter_row.addWidget(self.search_input)
        filter_row.addWidget(self.growth_filter)
        filter_row.addStretch()
        layout.addWidget(filter_box)

        list_box = QGroupBox("Список отделений")
        list_layout = QVBoxLayout(list_box)
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        self.list_widget.itemDoubleClicked.connect(self._open_selected)
        list_layout.addWidget(self.list_widget)
        layout.addWidget(list_box)
        layout.addStretch()

        self.refresh()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_quick_actions_panel"):
            self._quick_actions_panel.set_compact(self.width() < 1340)

    def _build_department_item(
        self, name: str, count: int, positives: int, last_text: str
    ) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("listCard")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        header = QHBoxLayout()
        header.setSpacing(6)
        status_dot = QLabel()
        status_dot.setObjectName("cardStatusDot")
        status_dot.setFixedSize(8, 8)
        status_dot.setProperty("tone", "danger" if positives > 0 else "ok")
        title = QLabel(name)
        title.setObjectName("cardTitle")
        header.addWidget(status_dot)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        meta = QLabel(f"Проб: {count} · Положительных: {positives}")
        meta.setObjectName("cardMeta")
        meta.setProperty("tone", "danger" if positives > 0 else "normal")
        last = QLabel(f"Последняя проба: {last_text}")
        last.setObjectName("muted")
        layout.addWidget(meta)
        layout.addWidget(last)
        return wrapper

    def refresh(self) -> None:
        self.list_widget.clear()
        filter_on = self.filter_enabled.isChecked()
        from_date = cast(date | None, self.date_from.date().toPython())
        to_date = cast(date | None, self.date_to.date().toPython())
        if filter_on and from_date and to_date and from_date > to_date:
            from_date, to_date = to_date, from_date
        search = self.search_input.text().strip().lower()
        growth_filter = self.growth_filter.currentData()
        total_samples = 0
        total_pos = 0
        dept_count = 0
        entries: list[dict[str, object]] = []
        for dep in self.reference_service.list_departments():
            dep_name = str(dep.name)
            if search and search not in dep_name.lower():
                continue
            dep_id = cast(int, dep.id)
            samples = self.sanitary_service.list_samples_by_department(dep_id)
            filtered = []
            if filter_on:
                for s in samples:
                    if not s.taken_at:
                        continue
                    s_date = s.taken_at.date()
                    if from_date and to_date and from_date <= s_date <= to_date:
                        filtered.append(s)
            else:
                filtered = samples
            count = len(filtered)
            positives = sum(1 for s in filtered if s.growth_flag == 1)
            if growth_filter == 1 and positives == 0:
                continue
            if growth_filter == 0 and all(s.growth_flag != 0 for s in filtered):
                continue
            if growth_filter == -1 and all(s.growth_flag is not None for s in filtered):
                continue
            total_samples += count
            total_pos += positives
            dept_count += 1
            last_dt: datetime | None = None
            for s in filtered:
                if s.taken_at and (last_dt is None or s.taken_at > last_dt):
                    last_dt = cast(datetime, s.taken_at)
            entries.append(
                {
                    "name": dep_name,
                    "dep_id": dep_id,
                    "count": count,
                    "positives": positives,
                    "last_dt": last_dt,
                }
            )
        entries.sort(
            key=lambda item: (
                item["positives"],
                item["count"],
                item["last_dt"] is not None,
                item["last_dt"] or 0,
            ),
            reverse=True,
        )
        if not entries:
            self._add_empty_item("Нет отделений по выбранным фильтрам.")
        for entry in entries:
            last_dt = cast(datetime | None, entry["last_dt"])
            last_text = last_dt.strftime("%d.%m.%Y %H:%M") if last_dt else "-"
            item = QListWidgetItem()
            card = self._build_department_item(
                cast(str, entry["name"]),
                cast(int, entry["count"]),
                cast(int, entry["positives"]),
                last_text,
            )
            item.setSizeHint(card.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, entry["dep_id"])
            item.setData(Qt.ItemDataRole.UserRole + 1, entry["name"])
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, card)
        self.summary_label.setText(
            f"Отделений: {dept_count}, проб: {total_samples}, положительных: {total_pos}"
        )

    def _add_empty_item(self, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.list_widget.addItem(item)

    def refresh_references(self) -> None:
        self.refresh()
        self.references_updated.emit()

    def _open_selected(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            return
        dep_id = item.data(Qt.ItemDataRole.UserRole)
        dep_name = item.data(Qt.ItemDataRole.UserRole + 1) or ""
        dlg = SanitaryHistoryDialog(
            self.sanitary_service,
            self.reference_service,
            department_id=dep_id,
            department_name=dep_name,
            parent=self,
        )
        dlg.exec()
