from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.services.emz_service import EmzService
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import clear_status, set_status


class CaseSearchDialog(QDialog):
    def __init__(self, emz_service: EmzService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.emz_service = emz_service
        self.selected_case_id: int | None = None
        self.setWindowTitle("Поиск госпитализации по пациенту")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.patient_id_input = QLineEdit()
        form.addRow("ID пациента", self.patient_id_input)
        layout.addLayout(form)

        btns = QHBoxLayout()
        search_btn = QPushButton("Найти")
        compact_button(search_btn)
        search_btn.clicked.connect(self._search)
        btns.addWidget(search_btn)
        btns.addStretch()
        layout.addLayout(btns)

        self.result_list = QListWidget()
        self.result_list.itemDoubleClicked.connect(self._accept_selected)
        layout.addWidget(self.result_list)

        self.status = QLabel("")
        self.status.setObjectName("statusLabel")
        layout.addWidget(self.status)

    def _search(self) -> None:
        self.result_list.clear()
        clear_status(self.status)
        try:
            pid = int(self.patient_id_input.text())
        except Exception:
            set_status(self.status, "Введите корректный ID пациента", "warning")
            return
        try:
            cases = self.emz_service.list_cases_by_patient(pid)
        except Exception as exc:  # noqa: BLE001
            set_status(self.status, str(exc), "error")
            return
        if not cases:
            set_status(self.status, "Госпитализации не найдены", "info")
            return
        for c in cases:
            item = QListWidgetItem(f"Госпитализация {c.id} v{c.version_no}")
            item.setData(Qt.ItemDataRole.UserRole, c.id)
            self.result_list.addItem(item)

    def _accept_selected(self) -> None:
        item = self.result_list.currentItem()
        if not item:
            return
        self.selected_case_id = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
