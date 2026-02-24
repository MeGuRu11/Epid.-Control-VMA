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

from app.application.services.patient_service import PatientService
from app.ui.widgets.async_task import run_async
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import clear_status, set_status


class PatientSearchDialog(QDialog):
    def __init__(
        self,
        patient_service: PatientService,
        parent: QWidget | None = None,
        *,
        initial_query: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.patient_service = patient_service
        self.selected_patient_id: int | None = None
        self.selected_name: str = ""
        self._initial_query = (initial_query or "").strip()
        self._search_token = 0
        self._recent_token = 0
        self.setWindowTitle("Поиск пациента")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("ФИО (минимум 3 символа)")
        self.query.returnPressed.connect(self._search)
        form.addRow("ФИО", self.query)
        layout.addLayout(form)

        btns = QHBoxLayout()
        self.search_btn = QPushButton("Поиск")
        compact_button(self.search_btn)
        self.search_btn.clicked.connect(self._search)
        btns.addWidget(self.search_btn)
        btns.addStretch()
        layout.addLayout(btns)

        results_label = QLabel("Результаты")
        layout.addWidget(results_label)
        self.result_list = QListWidget()
        self.result_list.itemDoubleClicked.connect(self._accept_selected)
        layout.addWidget(self.result_list)

        recent_label = QLabel("Последние пациенты")
        layout.addWidget(recent_label)
        self.recent_list = QListWidget()
        self.recent_list.itemDoubleClicked.connect(self._accept_selected)
        layout.addWidget(self.recent_list)

        action_row = QHBoxLayout()
        select_btn = QPushButton("Выбрать")
        compact_button(select_btn)
        select_btn.clicked.connect(self._accept_selected)
        close_btn = QPushButton("Закрыть")
        compact_button(close_btn)
        close_btn.clicked.connect(self.reject)
        action_row.addWidget(select_btn)
        action_row.addWidget(close_btn)
        action_row.addStretch()
        layout.addLayout(action_row)

        self.status = QLabel()
        self.status.setObjectName("statusLabel")
        layout.addWidget(self.status)

        self._load_recent()
        if self._initial_query:
            self.query.setText(self._initial_query)
            self._search()

    def _set_search_busy(self, busy: bool) -> None:
        self.search_btn.setEnabled(not busy)

    def _search(self) -> None:
        self.result_list.clear()
        clear_status(self.status)
        q = self.query.text().strip()
        if not q:
            self.status.setText("Введите ID или минимум 3 символа ФИО")
            return
        is_id_search = q.isdigit()
        if not is_id_search and len(q) < 3:
            self.status.setText("Введите ID или минимум 3 символа ФИО")
            return
        self._search_token += 1
        token = self._search_token
        self._set_search_busy(True)

        def _run() -> list:
            if is_id_search:
                patient = self.patient_service.get_by_id(int(q))
                return [patient]
            return self.patient_service.search_by_name(q, limit=20)

        def _on_success(patients: list) -> None:
            if token != self._search_token:
                return
            if not patients:
                self.status.setText("Пациент не найден")
                return
            for p in patients:
                label = f"{p.id}: {p.full_name} ({p.dob or '-'})"
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, (p.id, p.full_name))
                self.result_list.addItem(item)

        def _on_error(exc: Exception) -> None:
            if token != self._search_token:
                return
            set_status(self.status, str(exc), "error")

        run_async(
            self,
            _run,
            on_success=_on_success,
            on_error=_on_error,
            on_finished=lambda: self._set_search_busy(False),
        )

    def _load_recent(self) -> None:
        self.recent_list.clear()
        self._recent_token += 1
        token = self._recent_token

        def _run() -> list:
            return self.patient_service.list_recent(limit=10)

        def _on_success(patients: list) -> None:
            if token != self._recent_token:
                return
            for p in patients:
                label = f"{p.id}: {p.full_name} ({p.dob or '-'})"
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, (p.id, p.full_name))
                self.recent_list.addItem(item)

        def _on_error(exc: Exception) -> None:
            if token != self._recent_token:
                return
            self.status.setText(f"Не удалось загрузить последних пациентов: {exc}")

        run_async(self, _run, on_success=_on_success, on_error=_on_error)

    def _accept_selected(self, item: QListWidgetItem | None = None) -> None:
        if item is None:
            item = self.result_list.currentItem() or self.recent_list.currentItem()
        if not item:
            return
        pid, name = item.data(Qt.ItemDataRole.UserRole)
        self.selected_patient_id = pid
        self.selected_name = name
        self.accept()
