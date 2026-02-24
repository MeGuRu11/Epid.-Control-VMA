from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.services.patient_service import PatientService
from app.infrastructure.db.repositories.patient_repo import PatientRepository
from app.infrastructure.db.session import session_scope
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import clear_status, set_status


class PatientSelector(QWidget):
    """
    Simple patient selector by id/full_name/dob. Returns selected patient_id via callback.
    """

    def __init__(self, on_select, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.on_select = on_select
        self.repo = PatientRepository()
        self.patient_service = PatientService(self.repo, session_scope)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.patient_id = QLineEdit()
        self.search_query = QLineEdit()
        self.search_query.setPlaceholderText("ФИО пациента (>= 3 символа)")
        form.addRow("ID пациента", self.patient_id)
        form.addRow("ФИО (поиск)", self.search_query)
        layout.addLayout(form)
        btns = QHBoxLayout()
        apply_btn = QPushButton("Применить")
        compact_button(apply_btn)
        apply_btn.clicked.connect(self._apply)
        btns.addWidget(apply_btn)
        find_btn = QPushButton("Найти")
        compact_button(find_btn)
        find_btn.clicked.connect(self._open_search)
        btns.addWidget(find_btn)
        btns.addStretch()
        layout.addLayout(btns)
        self.status = QLabel("")
        self.status.setProperty("status_pill", True)
        set_status(self.status, "", "info")
        layout.addWidget(self.status)

    def _apply(self) -> None:
        clear_status(self.status)
        pid_text = self.patient_id.text().strip()
        if not pid_text:
            self._open_search()
            return
        try:
            pid = int(pid_text)
            if pid <= 0:
                raise ValueError
        except ValueError:
            set_status(self.status, "ID пациента должен быть положительным числом", "warning")
            return

        try:
            self.on_select(pid)
        except Exception as exc:  # noqa: BLE001
            set_status(self.status, f"Не удалось выбрать пациента: {exc}", "error")
            return

        name = self._get_patient_name(pid)
        label = f"Выбран: {name}" if name else "Выбран пациент"
        set_status(self.status, label, "success")

    def _open_search(self) -> None:
        from app.ui.widgets.patient_search_dialog import PatientSearchDialog

        query = self.search_query.text().strip()
        dlg = PatientSearchDialog(self.patient_service, parent=self, initial_query=query)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_patient_id:
            self.patient_id.setText(str(dlg.selected_patient_id))
            self.on_select(dlg.selected_patient_id)
            set_status(self.status, f"Выбран: {dlg.selected_name}", "success")
        else:
            if not query:
                set_status(self.status, "Укажите ID или введите ФИО для поиска", "warning")

    def set_patient_id(self, patient_id: int) -> None:
        self.patient_id.setText(str(patient_id))
        name = self._get_patient_name(patient_id)
        label = f"Выбран: {name}" if name else "Выбран пациент"
        set_status(self.status, label, "success")

    def clear(self) -> None:
        self.patient_id.clear()
        self.search_query.clear()
        clear_status(self.status)

    def _get_patient_name(self, patient_id: int) -> str | None:
        with session_scope() as session:
            patient = self.repo.get_by_id(session, patient_id)
            return str(patient.full_name) if patient else None
