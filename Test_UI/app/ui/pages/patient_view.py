from __future__ import annotations

from datetime import date

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...application.services.emr_service import EmrService
from ...application.services.patient_service import PatientService
from ..widgets.toast import show_toast


def _age(birth_date) -> str:
    if not birth_date:
        return "—"
    today = date.today()
    years = today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )
    return str(years)


def _fmt_date(d) -> str:
    if not d:
        return "—"
    try:
        return d.strftime("%d.%m.%Y")
    except Exception:
        return str(d)


def _fmt_sex(sex: str | None) -> str:
    return {"M": "Муж", "F": "Жен"}.get(sex or "", sex or "—")


class PatientView(QWidget):
    patientSelected = Signal(int)
    patientContextSelected = Signal(int)

    def __init__(self, engine, session_ctx):
        super().__init__()
        self._engine = engine
        self._session_ctx = session_ctx
        self.svc = PatientService(engine, session_ctx)
        self._emr_svc = EmrService(engine, session_ctx)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Поиск и ЭМК")
        title.setObjectName("title")
        layout.addWidget(title)

        # ── Поиск + кнопки ────────────────────────────────────────────────
        top = QHBoxLayout()
        self.q = QLineEdit()
        self.q.setPlaceholderText("Поиск по ФИО или ID")
        self.q.textChanged.connect(self.refresh)
        self.btn_select = QPushButton("Выбрать пациента")
        self.btn_select.setObjectName("secondary")
        self.btn_select.clicked.connect(self.select_patient_context)
        self.btn_new = QPushButton("Новый пациент")
        self.btn_new.clicked.connect(self.create_patient)
        self.btn_rename = QPushButton("Переименовать")
        self.btn_rename.setObjectName("secondary")
        self.btn_rename.clicked.connect(self.rename_patient)
        top.addWidget(self.q, 1)
        top.addWidget(self.btn_select)
        top.addWidget(self.btn_new)
        top.addWidget(self.btn_rename)
        layout.addLayout(top)

        # ── Таблица пациентов ─────────────────────────────────────────────
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "ФИО", "Пол", "Дата рождения", "Возраст"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellDoubleClicked.connect(lambda *_: self.open_in_emr())
        self.table.itemSelectionChanged.connect(self._on_patient_selection_changed)
        layout.addWidget(self.table, 2)

        self.btn_open = QPushButton("Открыть в ЭМЗ")
        self.btn_open.setObjectName("secondary")
        self.btn_open.clicked.connect(self.open_in_emr)
        layout.addWidget(self.btn_open, 0)

        # ── История госпитализаций ────────────────────────────────────────
        cases_card = QFrame()
        cases_card.setObjectName("card")
        cases_l = QVBoxLayout(cases_card)
        cases_l.setContentsMargins(12, 12, 12, 12)
        cases_l.setSpacing(6)

        cases_header = QHBoxLayout()
        cases_title = QLabel("История госпитализаций")
        cases_title.setObjectName("subtitle")
        cases_header.addWidget(cases_title)
        cases_header.addStretch(1)
        self.btn_open_case_emr = QPushButton("Открыть ЭМЗ")
        self.btn_open_case_emr.setObjectName("secondary")
        self.btn_open_case_emr.clicked.connect(self._open_case_in_emr)
        cases_header.addWidget(self.btn_open_case_emr)
        cases_l.addLayout(cases_header)

        self.cases_table = QTableWidget(0, 6)
        self.cases_table.setHorizontalHeaderLabels([
            "ID дела", "№ дела", "Отделение", "Поступление", "Выписка", "Тяжесть",
        ])
        self.cases_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.cases_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.cases_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.cases_table.setAlternatingRowColors(True)
        self.cases_table.verticalHeader().setVisible(False)
        self.cases_table.setMaximumHeight(160)
        chdr = self.cases_table.horizontalHeader()
        chdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        chdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        chdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        chdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        chdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        chdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.cases_table.doubleClicked.connect(self._open_case_in_emr)
        cases_l.addWidget(self.cases_table)

        self.cases_hint = QLabel("Выберите пациента, чтобы увидеть историю госпитализаций.")
        self.cases_hint.setObjectName("muted")
        cases_l.addWidget(self.cases_hint)
        layout.addWidget(cases_card, 1)

        self.refresh()

    def refresh(self):
        rows = self.svc.list(self.q.text().strip())
        self.table.setRowCount(len(rows))
        for idx, patient in enumerate(rows):
            birth = getattr(patient, "birth_date", None)
            self.table.setItem(idx, 0, QTableWidgetItem(str(patient.id)))
            self.table.setItem(idx, 1, QTableWidgetItem(patient.full_name or ""))
            self.table.setItem(idx, 2, QTableWidgetItem(_fmt_sex(patient.sex)))
            self.table.setItem(idx, 3, QTableWidgetItem(_fmt_date(birth)))
            self.table.setItem(idx, 4, QTableWidgetItem(_age(birth)))

    def _selected_patient_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return int(item.text())

    def _on_patient_selection_changed(self) -> None:
        patient_id = self._selected_patient_id()
        if patient_id is None:
            self.cases_table.setRowCount(0)
            self.cases_hint.setText("Выберите пациента, чтобы увидеть историю госпитализаций.")
            return
        self._load_cases(patient_id)

    def _load_cases(self, patient_id: int) -> None:
        try:
            cases = self._emr_svc.cases_for_patient(patient_id)
        except Exception:
            cases = []
        self.cases_table.setRowCount(0)
        for case in cases:
            try:
                ver = self._emr_svc.current_version(case.id)
            except Exception:
                ver = None
            r = self.cases_table.rowCount()
            self.cases_table.insertRow(r)
            self.cases_table.setItem(r, 0, QTableWidgetItem(str(case.id)))
            self.cases_table.setItem(r, 1, QTableWidgetItem(case.hospital_case_no or ""))
            self.cases_table.setItem(r, 2, QTableWidgetItem(case.department or ""))
            admission = str(ver.admission_date) if ver and ver.admission_date else ""
            outcome = str(ver.outcome_date) if ver and ver.outcome_date else ""
            severity = ver.severity or "" if ver else ""
            self.cases_table.setItem(r, 3, QTableWidgetItem(admission))
            self.cases_table.setItem(r, 4, QTableWidgetItem(outcome))
            self.cases_table.setItem(r, 5, QTableWidgetItem(severity))
        count = len(cases)
        self.cases_hint.setText(f"Госпитализаций: {count}. Двойной клик — открыть ЭМЗ.")

    def _open_case_in_emr(self, *_) -> None:
        patient_id = self._selected_patient_id()
        if patient_id is None:
            show_toast(self.window(), "Выберите пациента.", "warning")
            return
        self.patientSelected.emit(patient_id)

    def open_in_emr(self):
        patient_id = self._selected_patient_id()
        if patient_id is None:
            show_toast(self.window(), "Выберите пациента в таблице.", "warning")
            return
        self.patientSelected.emit(patient_id)

    def select_patient_context(self):
        patient_id = self._selected_patient_id()
        if patient_id is None:
            show_toast(self.window(), "Выберите пациента в таблице.", "warning")
            return
        self.patientContextSelected.emit(patient_id)
        show_toast(self.window(), f"Пациент {patient_id} выбран в контекст.", "success")

    def create_patient(self):
        full_name, ok = QInputDialog.getText(self, "Новый пациент", "ФИО:")
        if not ok or not full_name.strip():
            return
        self.svc.create(full_name.strip(), "M", None)
        show_toast(self.window(), "Пациент создан.", "success")
        self.refresh()

    def rename_patient(self):
        patient_id = self._selected_patient_id()
        if patient_id is None:
            show_toast(self.window(), "Выберите пациента в таблице.", "warning")
            return
        current_name = self.table.item(self.table.currentRow(), 1).text()
        full_name, ok = QInputDialog.getText(self, "Переименование", "Новое ФИО:", text=current_name)
        if not ok or not full_name.strip():
            return
        if self.svc.rename(patient_id, full_name.strip()):
            show_toast(self.window(), "Карточка пациента обновлена.", "success")
            self.refresh()
        else:
            show_toast(self.window(), "Пациент не найден.", "error")
