from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.patient_dto import PatientResponse
from app.application.services.patient_service import PatientService
from app.ui.widgets.async_task import run_async
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import clear_status, set_status
from app.ui.widgets.table_utils import resize_columns_to_content, set_table_read_only


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
        self._picker_rows: list[PatientResponse] = []
        self._picker_token = 0
        self.setWindowTitle("Поиск пациента")
        self.setMinimumSize(640, 520)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Поиск пациента")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        helper = QLabel("Выберите пациента из полного списка или отфильтруйте его по ФИО / ID.")
        helper.setObjectName("muted")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        search_row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("ФИО или ID пациента")
        self.query.setText(self._initial_query)
        self.query.returnPressed.connect(self._search)
        search_row.addWidget(self.query, 1)

        self.search_btn = QPushButton("Поиск")
        compact_button(self.search_btn)
        self.search_btn.clicked.connect(self._search)
        search_row.addWidget(self.search_btn)

        self.reset_btn = QPushButton("Сбросить")
        compact_button(self.reset_btn)
        self.reset_btn.clicked.connect(self._reset_filter)
        search_row.addWidget(self.reset_btn)
        layout.addLayout(search_row)

        self.count_label = QLabel("Пациентов: 0")
        self.count_label.setObjectName("chipLabel")
        layout.addWidget(self.count_label)

        self.result_table = QTableWidget(0, 3)
        self.result_table.setHorizontalHeaderLabels(["ID", "ФИО", "Дата рождения"])
        self.result_table.horizontalHeader().setStretchLastSection(False)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.result_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.result_table.setMinimumHeight(320)
        set_table_read_only(self.result_table)
        self.result_table.itemDoubleClicked.connect(self._accept_selected)
        layout.addWidget(self.result_table)

        action_row = QHBoxLayout()
        action_row.addStretch()
        select_btn = QPushButton("Выбрать")
        compact_button(select_btn)
        select_btn.clicked.connect(self._accept_selected)
        close_btn = QPushButton("Закрыть")
        compact_button(close_btn)
        close_btn.clicked.connect(self.reject)
        action_row.addWidget(select_btn)
        action_row.addWidget(close_btn)
        layout.addLayout(action_row)

        self.status = QLabel("")
        self.status.setObjectName("statusLabel")
        layout.addWidget(self.status)

        self._load_picker_rows()

    def _set_search_busy(self, busy: bool) -> None:
        self.search_btn.setEnabled(not busy)
        self.reset_btn.setEnabled(not busy)

    def _clear_status(self) -> None:
        if isinstance(self.status, QLabel):
            clear_status(self.status)
            return
        if hasattr(self.status, "setText"):
            self.status.setText("")

    def _set_status(self, message: str, level: str = "info") -> None:
        if isinstance(self.status, QLabel):
            set_status(self.status, message, level)
            return
        if hasattr(self.status, "setText"):
            self.status.setText(message)

    def _clear_results(self) -> None:
        if hasattr(self.result_table, "clearContents"):
            self.result_table.clearContents()
        elif hasattr(self.result_table, "clear"):
            self.result_table.clear()
        if hasattr(self.result_table, "setRowCount"):
            self.result_table.setRowCount(0)

    def _load_picker_rows(self) -> None:
        self._picker_token += 1
        token = self._picker_token
        clear_results = getattr(self, "_clear_results", None)
        if callable(clear_results):
            clear_results()
        clear_status_handler = getattr(self, "_clear_status", None)
        if callable(clear_status_handler):
            clear_status_handler()
        if hasattr(self, "count_label") and hasattr(self.count_label, "setText"):
            self.count_label.setText("Пациентов: 0")
        set_search_busy = getattr(self, "_set_search_busy", None)
        if callable(set_search_busy):
            set_search_busy(True)

        def _run() -> list[PatientResponse]:
            return self.patient_service.list_for_picker()

        def _on_success(patients: list[PatientResponse]) -> None:
            if token != self._picker_token:
                return
            self._picker_rows = list(patients)
            self._apply_filtered_rows(self.query.text().strip())

        def _on_error(exc: Exception) -> None:
            if token != self._picker_token:
                return
            set_status_handler = getattr(self, "_set_status", None)
            if callable(set_status_handler):
                set_status_handler(f"Не удалось загрузить список пациентов: {exc}", "error")
            elif hasattr(self, "status") and hasattr(self.status, "setText"):
                self.status.setText(f"Не удалось загрузить список пациентов: {exc}")

        run_async(
            self,
            _run,
            on_success=_on_success,
            on_error=_on_error,
            on_finished=lambda: set_search_busy(False) if callable(set_search_busy) else None,
        )

    def _search(self) -> None:
        self._clear_status()
        self._apply_filtered_rows(self.query.text().strip())

    def _reset_filter(self) -> None:
        self.query.clear()
        self._clear_status()
        self._apply_patient_rows(self._picker_rows)

    def _apply_filtered_rows(self, query: str) -> None:
        normalized = query.casefold().strip()
        if not normalized:
            self._apply_patient_rows(self._picker_rows)
            return

        filtered: list[PatientResponse] = []
        for patient in self._picker_rows:
            if normalized in str(patient.id):
                filtered.append(patient)
                continue
            if normalized in patient.full_name.casefold():
                filtered.append(patient)
                continue
            if patient.dob and normalized in patient.dob.strftime("%d.%m.%Y").casefold():
                filtered.append(patient)

        self._apply_patient_rows(filtered)
        if not filtered:
            self._set_status("Пациенты не найдены", "warning")

    def _apply_patient_rows(self, patients: Sequence[PatientResponse]) -> None:
        self._clear_results()
        if hasattr(self.result_table, "setRowCount"):
            self.result_table.setRowCount(len(patients))
        for row_index, patient in enumerate(patients):
            dob_text = patient.dob.strftime("%d.%m.%Y") if patient.dob else "—"
            row_values = (str(patient.id), patient.full_name, dob_text)
            for column_index, text in enumerate(row_values):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, (patient.id, patient.full_name))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.result_table.setItem(row_index, column_index, item)
        if patients:
            resize_columns_to_content(self.result_table)
            self.result_table.setColumnWidth(0, max(80, self.result_table.columnWidth(0)))
            self.result_table.setColumnWidth(2, max(130, self.result_table.columnWidth(2)))
            self.result_table.selectRow(0)
        self.count_label.setText(f"Пациентов: {len(patients)}")

    def _accept_selected(self, item: QTableWidgetItem | None = None) -> None:
        if item is None:
            item = self.result_table.currentItem()
        if not item:
            self._set_status("Выберите пациента из списка", "warning")
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, tuple) or len(data) != 2:
            self._set_status("Не удалось прочитать выбранного пациента", "error")
            return
        patient_id, name = data
        self.selected_patient_id = int(patient_id)
        self.selected_name = str(name)
        self.accept()
