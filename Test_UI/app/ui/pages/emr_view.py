from __future__ import annotations

from datetime import date, datetime
from typing import cast

from PySide6.QtCore import QDate, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...application.services.emr_service import EmrService
from ...application.services.reference_service import ReferenceService
from ..widgets.toast import show_toast

_KIND_DISPLAY = {"admission": "поступление", "discharge": "выписка", "complication": "осложнение"}
_KIND_DB = {v: k for k, v in _KIND_DISPLAY.items()}

_INTVN_DISPLAY = {
    "central_catheter": "ЦВК",
    "urinary_catheter": "Мочевой катетер",
    "ventilation": "ИВЛ",
    "surgery": "Операция",
    "other": "Другое",
}
_INTVN_DB = {v: k for k, v in _INTVN_DISPLAY.items()}


def _to_date(qd: QDate) -> date | None:
    if not qd or not qd.isValid():
        return None
    return date(qd.year(), qd.month(), qd.day())


def _set_qdate(widget: QDateEdit, value: date | None) -> None:
    if value is None:
        widget.setDate(QDate.currentDate())
        return
    widget.setDate(QDate(value.year, value.month, value.day))


def _dt_str(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d")


def _parse_date_str(s: str) -> datetime | None:
    s = s.strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _make_table(headers: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    t.verticalHeader().setVisible(False)
    t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    t.setAlternatingRowColors(True)
    t.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    t.setMaximumHeight(200)
    return t


def _table_btn_row(add_fn, remove_fn) -> QHBoxLayout:
    row = QHBoxLayout()
    btn_add = QPushButton("+ Добавить строку")
    btn_add.setObjectName("secondary")
    btn_add.clicked.connect(add_fn)
    btn_rem = QPushButton("— Удалить выбранную")
    btn_rem.setObjectName("ghost")
    btn_rem.clicked.connect(remove_fn)
    row.addWidget(btn_add)
    row.addWidget(btn_rem)
    row.addStretch(1)
    return row


class EmrView(QWidget):
    backRequested = Signal()
    caseSelected = Signal(int)
    createForm100Requested = Signal()

    def __init__(self, engine, session_ctx):
        super().__init__()
        self.svc = EmrService(engine, session_ctx)
        self.ref_svc = ReferenceService(engine, session_ctx)
        self.patient_id: int | None = None
        self.case_id: int | None = None
        self._current_version_id: int | None = None
        self._abx_list: list = []  # cached antibiotics for combos
        self._dirty = False

        # ── Outer layout ──────────────────────────────────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 8)
        outer.setSpacing(8)

        # Header
        head = QHBoxLayout()
        title = QLabel("ЭМЗ")
        title.setObjectName("title")
        head.addWidget(title, 1)
        self.btn_back = QPushButton("Назад")
        self.btn_back.setObjectName("ghost")
        self.btn_back.clicked.connect(self.backRequested.emit)
        head.addWidget(self.btn_back)
        outer.addLayout(head)



        # ── Scroll area ───────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll, 1)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(10)

        # ── Основные поля ─────────────────────────────────────────────────
        top_form = QFormLayout()
        top_form.setSpacing(6)
        self.case_no = QLineEdit()
        self.case_no.setPlaceholderText("№ ИБ")
        self.dep = QLineEdit()
        self.dep.setPlaceholderText("Отделение")
        top_form.addRow("Номер госпитализации", self.case_no)
        top_form.addRow("Отделение", self.dep)
        layout.addLayout(top_form)

        dates_row = QHBoxLayout()
        self.adm = QDateEdit()
        self.adm.setCalendarPopup(True)
        self.adm.setDisplayFormat("yyyy-MM-dd")
        self.inj = QDateEdit()
        self.inj.setCalendarPopup(True)
        self.inj.setDisplayFormat("yyyy-MM-dd")
        self.out = QDateEdit()
        self.out.setCalendarPopup(True)
        self.out.setDisplayFormat("yyyy-MM-dd")
        dates_row.addWidget(QLabel("Поступление"))
        dates_row.addWidget(self.adm)
        dates_row.addWidget(QLabel("Травма"))
        dates_row.addWidget(self.inj)
        dates_row.addWidget(QLabel("Исход"))
        dates_row.addWidget(self.out)
        layout.addLayout(dates_row)

        metrics_row = QHBoxLayout()
        self.sev = QComboBox()
        self.sev.addItems(["", "легкая", "средняя", "тяжелая"])
        self.sofa = QSpinBox()
        self.sofa.setRange(0, 40)
        metrics_row.addWidget(QLabel("Тяжесть"))
        metrics_row.addWidget(self.sev)
        metrics_row.addWidget(QLabel("SOFA"))
        metrics_row.addWidget(self.sofa)
        metrics_row.addStretch(1)
        layout.addLayout(metrics_row)

        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Клинические заметки...")
        self.notes.setFixedHeight(72)
        layout.addWidget(self.notes)

        # ── Диагнозы ─────────────────────────────────────────────────────
        grp_diag = QGroupBox("Диагнозы (МКБ-10)")
        grp_diag_l = QVBoxLayout(grp_diag)
        grp_diag_l.setSpacing(4)
        self.tbl_diag = _make_table(["Вид", "Код МКБ-10", "Свободный текст"])
        grp_diag_l.addWidget(self.tbl_diag)
        grp_diag_l.addLayout(_table_btn_row(self._diag_add_row, self._diag_remove_row))
        layout.addWidget(grp_diag)

        # ── Вмешательства ─────────────────────────────────────────────────
        grp_intvn = QGroupBox("Вмешательства (факторы риска ИСМП)")
        grp_intvn_l = QVBoxLayout(grp_intvn)
        grp_intvn_l.setSpacing(4)
        self.tbl_intvn = _make_table(["Тип", "Начало (ГГГГ-ММ-ДД)", "Конец (ГГГГ-ММ-ДД)", "Исполнитель", "Примечания"])
        grp_intvn_l.addWidget(self.tbl_intvn)
        grp_intvn_l.addLayout(_table_btn_row(self._intvn_add_row, self._intvn_remove_row))
        layout.addWidget(grp_intvn)

        # ── Курсы антибиотиков ────────────────────────────────────────────
        grp_abx = QGroupBox("Курсы антибиотикотерапии")
        grp_abx_l = QVBoxLayout(grp_abx)
        grp_abx_l.setSpacing(4)
        self.tbl_abx = _make_table(["Антибиотик", "Своб. название", "Начало", "Конец", "Путь", "Доза"])
        grp_abx_l.addWidget(self.tbl_abx)
        grp_abx_l.addLayout(_table_btn_row(self._abx_add_row, self._abx_remove_row))
        layout.addWidget(grp_abx)

        layout.addStretch(1)

        # ── Кнопки внизу (вне scroll) ─────────────────────────────────────
        buttons = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить как новую версию")
        self.btn_hist = QPushButton("История версий / Undo")
        self.btn_hist.setObjectName("secondary")
        self.btn_form100 = QPushButton("📋  Создать Форму 100")
        self.btn_form100.setObjectName("secondary")
        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_hist)
        buttons.addWidget(self.btn_form100)
        buttons.addStretch(1)
        outer.addLayout(buttons)

        self.btn_save.clicked.connect(self.save_new_version)
        self.btn_hist.clicked.connect(self.open_history)
        self.btn_form100.clicked.connect(self.createForm100Requested.emit)

        # ── Подключаем поля к флагу изменений ────────────────────────────
        self.case_no.textChanged.connect(self._mark_dirty)
        self.dep.textChanged.connect(self._mark_dirty)
        self.adm.dateChanged.connect(self._mark_dirty)
        self.inj.dateChanged.connect(self._mark_dirty)
        self.out.dateChanged.connect(self._mark_dirty)
        self.sev.currentIndexChanged.connect(self._mark_dirty)
        self.sofa.valueChanged.connect(self._mark_dirty)
        self.notes.textChanged.connect(self._mark_dirty)

        # ── Таймер автосохранения (60 сек) ────────────────────────────────
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setInterval(60_000)
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._auto_save_timer.start()

    # ── Diagnoses table helpers ───────────────────────────────────────────
    def _diag_add_row(self, kind: str = "admission", icd_code: str = "", free_text: str = "") -> None:
        r = self.tbl_diag.rowCount()
        self.tbl_diag.insertRow(r)
        combo = QComboBox()
        combo.addItems(list(_KIND_DISPLAY.values()))
        combo.setCurrentText(_KIND_DISPLAY.get(kind, "поступление"))
        self.tbl_diag.setCellWidget(r, 0, combo)
        self.tbl_diag.setItem(r, 1, QTableWidgetItem(icd_code))
        self.tbl_diag.setItem(r, 2, QTableWidgetItem(free_text))

    def _diag_remove_row(self) -> None:
        rows = sorted({i.row() for i in self.tbl_diag.selectedItems()}, reverse=True)
        for r in rows:
            self.tbl_diag.removeRow(r)

    def _collect_diagnoses(self) -> list[dict]:
        result = []
        for r in range(self.tbl_diag.rowCount()):
            combo = cast(QComboBox, self.tbl_diag.cellWidget(r, 0))
            kind_display = combo.currentText() if combo else "поступление"
            kind = _KIND_DB.get(kind_display, "admission")
            icd = (self.tbl_diag.item(r, 1) or QTableWidgetItem("")).text().strip() or None
            free = (self.tbl_diag.item(r, 2) or QTableWidgetItem("")).text().strip() or None
            result.append({"kind": kind, "icd10_code": icd, "free_text": free})
        return result

    # ── Interventions table helpers ───────────────────────────────────────
    def _intvn_add_row(
        self,
        itype: str = "other",
        start: str = "",
        end: str = "",
        performed_by: str = "",
        notes: str = "",
    ) -> None:
        r = self.tbl_intvn.rowCount()
        self.tbl_intvn.insertRow(r)
        combo = QComboBox()
        combo.addItems(list(_INTVN_DISPLAY.values()))
        combo.setCurrentText(_INTVN_DISPLAY.get(itype, "Другое"))
        self.tbl_intvn.setCellWidget(r, 0, combo)
        self.tbl_intvn.setItem(r, 1, QTableWidgetItem(start))
        self.tbl_intvn.setItem(r, 2, QTableWidgetItem(end))
        self.tbl_intvn.setItem(r, 3, QTableWidgetItem(performed_by))
        self.tbl_intvn.setItem(r, 4, QTableWidgetItem(notes))

    def _intvn_remove_row(self) -> None:
        rows = sorted({i.row() for i in self.tbl_intvn.selectedItems()}, reverse=True)
        for r in rows:
            self.tbl_intvn.removeRow(r)

    def _collect_interventions(self) -> list[dict]:
        result = []
        for r in range(self.tbl_intvn.rowCount()):
            combo = cast(QComboBox, self.tbl_intvn.cellWidget(r, 0))
            type_display = combo.currentText() if combo else "Другое"
            itype = _INTVN_DB.get(type_display, "other")
            start = _parse_date_str((self.tbl_intvn.item(r, 1) or QTableWidgetItem("")).text())
            end = _parse_date_str((self.tbl_intvn.item(r, 2) or QTableWidgetItem("")).text())
            performed_by = (self.tbl_intvn.item(r, 3) or QTableWidgetItem("")).text().strip() or None
            notes = (self.tbl_intvn.item(r, 4) or QTableWidgetItem("")).text().strip() or None
            result.append(
                {"type": itype, "start_dt": start, "end_dt": end, "performed_by": performed_by, "notes": notes}
            )
        return result

    # ── ABx table helpers ─────────────────────────────────────────────────
    def _abx_add_row(
        self,
        antibiotic_id: int | None = None,
        drug_free: str = "",
        start: str = "",
        end: str = "",
        route: str = "",
        dose: str = "",
    ) -> None:
        r = self.tbl_abx.rowCount()
        self.tbl_abx.insertRow(r)
        combo = QComboBox()
        combo.addItem("— (своб. название)", None)
        for abx in self._abx_list:
            combo.addItem(f"{abx.name}", abx.id)
        if antibiotic_id is not None:
            for i in range(combo.count()):
                if combo.itemData(i) == antibiotic_id:
                    combo.setCurrentIndex(i)
                    break
        self.tbl_abx.setCellWidget(r, 0, combo)
        self.tbl_abx.setItem(r, 1, QTableWidgetItem(drug_free))
        self.tbl_abx.setItem(r, 2, QTableWidgetItem(start))
        self.tbl_abx.setItem(r, 3, QTableWidgetItem(end))
        self.tbl_abx.setItem(r, 4, QTableWidgetItem(route))
        self.tbl_abx.setItem(r, 5, QTableWidgetItem(dose))

    def _abx_remove_row(self) -> None:
        rows = sorted({i.row() for i in self.tbl_abx.selectedItems()}, reverse=True)
        for r in rows:
            self.tbl_abx.removeRow(r)

    def _collect_abx(self) -> list[dict]:
        result = []
        for r in range(self.tbl_abx.rowCount()):
            combo = cast(QComboBox, self.tbl_abx.cellWidget(r, 0))
            abx_id = combo.currentData() if combo else None
            drug_free = (self.tbl_abx.item(r, 1) or QTableWidgetItem("")).text().strip() or None
            start = _parse_date_str((self.tbl_abx.item(r, 2) or QTableWidgetItem("")).text())
            end = _parse_date_str((self.tbl_abx.item(r, 3) or QTableWidgetItem("")).text())
            route = (self.tbl_abx.item(r, 4) or QTableWidgetItem("")).text().strip() or None
            dose = (self.tbl_abx.item(r, 5) or QTableWidgetItem("")).text().strip() or None
            result.append(
                {
                    "antibiotic_id": abx_id,
                    "drug_name_free": drug_free,
                    "start_dt": start,
                    "end_dt": end,
                    "route": route,
                    "dose": dose,
                }
            )
        return result

    # ── Dirty / autosave ──────────────────────────────────────────────────
    def _mark_dirty(self, *_) -> None:
        self._dirty = True

    def _auto_save(self) -> None:
        if not self._dirty:
            return
        if not self.patient_id or not self.case_no.text().strip():
            return
        try:
            case_no = self.case_no.text().strip()
            self.case_id = self.svc.ensure_case(self.patient_id, case_no, self.dep.text().strip())
            payload = {
                "admission_date": _to_date(self.adm.date()),
                "injury_date": _to_date(self.inj.date()),
                "outcome_date": _to_date(self.out.date()),
                "severity": self.sev.currentText() or None,
                "sofa_score": int(self.sofa.value()),
                "notes": self.notes.toPlainText().strip() or None,
            }
            version_id = self.svc.create_new_version(self.case_id, payload)
            self._current_version_id = version_id
            self.svc.save_children(
                version_id,
                diagnoses=self._collect_diagnoses(),
                interventions=self._collect_interventions(),
                abx_courses=self._collect_abx(),
            )
            self._dirty = False
            self.caseSelected.emit(self.case_id)
        except Exception:
            show_toast(self.window(), "Ошибка автосохранения ЭМЗ.", "error")

    # ── Context ───────────────────────────────────────────────────────────
    def _reload_abx_cache(self) -> None:
        try:
            self._abx_list = self.ref_svc.antibiotics()
        except Exception:
            self._abx_list = []

    def _clear_children_tables(self) -> None:
        self.tbl_diag.setRowCount(0)
        self.tbl_intvn.setRowCount(0)
        self.tbl_abx.setRowCount(0)

    def set_context(self, patient_id: int):
        self.patient_id = patient_id
        self.case_id = None
        self._current_version_id = None
        today = QDate.currentDate()
        self.adm.setDate(today)
        self.inj.setDate(today)
        self.out.setDate(today)
        self.case_no.clear()
        self.dep.clear()
        self.notes.clear()
        self.sev.setCurrentIndex(0)
        self.sofa.setValue(0)
        self._reload_abx_cache()
        self._clear_children_tables()
        self._dirty = False

    def set_case_context(self, case_id: int | None) -> None:
        if self.patient_id is None:
            return
        if case_id is None:
            self.case_id = None
            self._current_version_id = None
            self._clear_children_tables()
            return
        cases = self.svc.cases_for_patient(self.patient_id)
        selected_case = next((c for c in cases if int(c.id) == int(case_id)), None)
        if selected_case is None:
            self.case_id = None
            self._current_version_id = None
            self._clear_children_tables()
            return

        self.case_id = int(selected_case.id)
        self.case_no.setText(selected_case.hospital_case_no or "")
        self.dep.setText(selected_case.department or "")
        self._reload_abx_cache()
        self._clear_children_tables()
        self._dirty = False

        version = self.svc.current_version(self.case_id)
        if version is not None:
            self._current_version_id = int(version.id)
            _set_qdate(self.adm, version.admission_date)
            _set_qdate(self.inj, version.injury_date)
            _set_qdate(self.out, version.outcome_date)
            severity = version.severity or ""
            idx = self.sev.findText(severity)
            self.sev.setCurrentIndex(idx if idx >= 0 else 0)
            self.sofa.setValue(int(version.sofa_score or 0))
            self.notes.setPlainText(version.notes or "")
            self._load_children(self._current_version_id)

    def _load_children(self, version_id: int) -> None:
        try:
            children = self.svc.get_children(version_id)
        except Exception:
            return

        for d in children.get("diagnoses", []):
            self._diag_add_row(
                kind=d.kind or "admission",
                icd_code=d.icd10_code or "",
                free_text=d.free_text or "",
            )

        for iv in children.get("interventions", []):
            self._intvn_add_row(
                itype=iv.type or "other",
                start=_dt_str(iv.start_dt),
                end=_dt_str(iv.end_dt),
                performed_by=iv.performed_by or "",
                notes=iv.notes or "",
            )

        for abx in children.get("abx_courses", []):
            self._abx_add_row(
                antibiotic_id=abx.antibiotic_id,
                drug_free=abx.drug_name_free or "",
                start=_dt_str(abx.start_dt),
                end=_dt_str(abx.end_dt),
                route=abx.route or "",
                dose=abx.dose or "",
            )

    # ── Save ──────────────────────────────────────────────────────────────
    def save_new_version(self):
        if not self.patient_id:
            show_toast(self.window(), "Сначала выберите пациента.", "warning")
            return
        case_no = self.case_no.text().strip()
        if not case_no:
            show_toast(self.window(), "Заполните номер госпитализации.", "warning")
            return

        try:
            self.case_id = self.svc.ensure_case(self.patient_id, case_no, self.dep.text().strip())
            payload = {
                "admission_date": _to_date(self.adm.date()),
                "injury_date": _to_date(self.inj.date()),
                "outcome_date": _to_date(self.out.date()),
                "severity": self.sev.currentText() or None,
                "sofa_score": int(self.sofa.value()),
                "notes": self.notes.toPlainText().strip() or None,
            }
            version_id = self.svc.create_new_version(self.case_id, payload)
            self._current_version_id = version_id
            self.svc.save_children(
                version_id,
                diagnoses=self._collect_diagnoses(),
                interventions=self._collect_interventions(),
                abx_courses=self._collect_abx(),
            )
            self.caseSelected.emit(self.case_id)
            show_toast(self.window(), "Новая версия ЭМЗ сохранена.", "success")
        except ValueError as exc:
            show_toast(self.window(), str(exc), "warning")
        except Exception as exc:
            show_toast(self.window(), f"Ошибка сохранения: {exc}", "error")

    def open_history(self):
        if not self.case_id:
            show_toast(self.window(), "Сначала сохраните хотя бы одну версию.", "info")
            return
        versions = self.svc.versions(self.case_id)
        if not versions:
            show_toast(self.window(), "История версий пуста.", "info")
            return

        items = [
            f"v{v.version_no} | {v.valid_from.isoformat()} | SOFA={v.sofa_score} | {v.severity or '-'}"
            for v in versions
        ]
        selected, ok = QInputDialog.getItem(
            self,
            "История версий",
            "Выберите версию для Undo (будет создана новая текущая):",
            items,
            0,
            False,
        )
        if not ok:
            return
        idx = items.index(selected)
        self.svc.restore_version_as_new(versions[idx].id)
        show_toast(self.window(), "Undo выполнен: создана новая текущая версия.", "success")
