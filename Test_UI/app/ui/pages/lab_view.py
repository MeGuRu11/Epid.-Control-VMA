from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...application.services.lab_service import LabService
from ...application.services.reference_service import ReferenceService
from ..lab.lab_sample_detail_dialog import LabSampleDetailDialog
from ..widgets.toast import show_toast

_PAGE_SIZE = 50


class _PatientBanner(QFrame):
    """Premium patient context bar shown below the page title."""

    _STYLE_EMPTY = (
        "QFrame#patientBanner {"
        "  background: #F9F4EE;"
        "  border: 1px solid #E3D9CF;"
        "  border-radius: 10px;"
        "}"
    )
    _STYLE_FILLED = (
        "QFrame#patientBanner {"
        "  background: rgba(143, 220, 207, 0.12);"
        "  border: 1px solid rgba(111, 185, 173, 0.55);"
        "  border-radius: 10px;"
        "}"
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("patientBanner")
        self.setFixedHeight(52)
        self.setStyleSheet(self._STYLE_EMPTY)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(14)

        self._icon = QLabel("\U0001f464")
        self._icon.setStyleSheet(
            "font-size: 20px; background: transparent; border: none;"
        )
        lay.addWidget(self._icon)

        col = QVBoxLayout()
        col.setSpacing(1)
        self._name = QLabel("Пациент не выбран")
        self._name.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #2F3135;"
            " background: transparent; border: none;"
        )
        self._sub = QLabel("Выберите пациента через панель контекста")
        self._sub.setStyleSheet(
            "font-size: 11px; color: #9A9490;"
            " background: transparent; border: none;"
        )
        col.addWidget(self._name)
        col.addWidget(self._sub)
        lay.addLayout(col, 1)

        self._case_badge = QLabel()
        self._case_badge.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #2E7D6A;"
            " background: rgba(143, 220, 207, 0.22);"
            " border: 1px solid rgba(111, 185, 173, 0.55);"
            " border-radius: 8px; padding: 3px 10px;"
        )
        self._case_badge.setVisible(False)
        lay.addWidget(self._case_badge)

    def set_patient(
        self, name: str | None, case_id: int | None
    ) -> None:
        if name:
            self.setStyleSheet(self._STYLE_FILLED)
            self._icon.setText("\U0001f464")
            self._name.setText(name)
            sub = "Пациент выбран"
            if case_id:
                sub += f"   \u2022   Госпитализация #{case_id}"
            else:
                sub += "   \u2022   Госпитализация не выбрана"
            self._sub.setText(sub)
            self._sub.setStyleSheet(
                "font-size: 11px; color: #4A7A6E;"
                " background: transparent; border: none;"
            )
            if case_id:
                self._case_badge.setText(f"\U0001f4cb  ИБ #{case_id}")
                self._case_badge.setVisible(True)
            else:
                self._case_badge.setVisible(False)
        else:
            self.setStyleSheet(self._STYLE_EMPTY)
            self._icon.setText("\u2139")
            self._name.setText("Пациент не выбран")
            self._sub.setText("Выберите пациента через панель контекста")
            self._sub.setStyleSheet(
                "font-size: 11px; color: #9A9490;"
                " background: transparent; border: none;"
            )
            self._case_badge.setVisible(False)


class LabView(QWidget):
    def __init__(self, engine, session_ctx):
        super().__init__()
        self._engine = engine
        self._session_ctx = session_ctx
        self._svc = LabService(engine, session_ctx)
        self._ref_svc = ReferenceService(engine, session_ctx)
        self._context_patient_id: int | None = None
        self._context_case_id: int | None = None
        self._context_patient_name: str | None = None
        self._all_samples: list = []
        self._filtered: list = []
        self._page = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # ── Заголовок ─────────────────────────────────────────────────────
        title = QLabel("Лаборатория")
        title.setObjectName("title")
        layout.addWidget(title)

        self._patient_banner = _PatientBanner()
        layout.addWidget(self._patient_banner)

        # ── Фильтры ───────────────────────────────────────────────────────
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Вид материала:"))
        self.filter_mat = QComboBox()
        self.filter_mat.setMinimumWidth(140)
        filter_row.addWidget(self.filter_mat)
        filter_row.addWidget(QLabel("Рост:"))
        self.filter_growth = QComboBox()
        self.filter_growth.addItems(["Все", "Рост", "Нет роста"])
        filter_row.addWidget(self.filter_growth)
        btn_apply = QPushButton("Применить")
        btn_apply.setObjectName("secondary")
        btn_apply.clicked.connect(self._apply_filters)
        btn_reset = QPushButton("Сброс")
        btn_reset.setObjectName("ghost")
        btn_reset.clicked.connect(self._reset_filters)
        filter_row.addWidget(btn_apply)
        filter_row.addWidget(btn_reset)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        # ── Действия ──────────────────────────────────────────────────────
        actions = QHBoxLayout()
        self.btn_new_auto = QPushButton("Новая проба (auto №)")
        self.btn_new_auto.clicked.connect(self.create_auto_sample)
        self.btn_new_manual = QPushButton("Новая проба (ручной №)")
        self.btn_new_manual.setObjectName("secondary")
        self.btn_new_manual.clicked.connect(self.create_manual_sample)
        btn_refresh = QPushButton("Обновить")
        btn_refresh.setObjectName("ghost")
        btn_refresh.clicked.connect(self.refresh)
        actions.addWidget(self.btn_new_auto)
        actions.addWidget(self.btn_new_manual)
        actions.addWidget(btn_refresh)
        actions.addStretch(1)
        layout.addLayout(actions)

        # ── Таблица ───────────────────────────────────────────────────────
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Пациент", "Случай", "Lab №", "Barcode", "Дата взятия", "Материал", "Организм", "Рост"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        self.table.doubleClicked.connect(self._open_detail)
        layout.addWidget(self.table, 1)

        hint = QLabel("Двойной клик — открыть карточку пробы")
        hint.setObjectName("muted")
        layout.addWidget(hint)

        # ── Пагинация ─────────────────────────────────────────────────────
        pag_row = QHBoxLayout()
        self.btn_prev = QPushButton("◀ Назад")
        self.btn_prev.setObjectName("ghost")
        self.btn_prev.clicked.connect(self._prev_page)
        self.page_label = QLabel("Страница 1 / 1")
        self.page_label.setObjectName("muted")
        self.btn_next = QPushButton("Далее ▶")
        self.btn_next.setObjectName("ghost")
        self.btn_next.clicked.connect(self._next_page)
        pag_row.addWidget(self.btn_prev)
        pag_row.addWidget(self.page_label)
        pag_row.addWidget(self.btn_next)
        pag_row.addStretch(1)
        layout.addLayout(pag_row)

        self._load_material_types()
        self.refresh()

    def _load_material_types(self) -> None:
        self.filter_mat.clear()
        self.filter_mat.addItem("Все", None)
        try:
            for mt in self._ref_svc.material_types():
                self.filter_mat.addItem(mt.name, mt.id)
        except Exception:
            pass

    def set_context(
        self,
        patient_id: int | None,
        case_id: int | None,
        patient_name: str | None = None,
    ) -> None:
        self._context_patient_id = patient_id
        self._context_case_id = case_id
        if patient_name is not None:
            self._context_patient_name = patient_name
        elif patient_id is None:
            self._context_patient_name = None
        self._patient_banner.set_patient(self._context_patient_name, case_id)
        self.refresh()

    def refresh(self) -> None:
        self._page = 0
        self._all_samples = self._svc.list(
            patient_id=self._context_patient_id,
            emr_case_id=self._context_case_id,
        )
        self._apply_filters()

    def _apply_filters(self) -> None:
        mat_id = self.filter_mat.currentData()
        growth_filter = self.filter_growth.currentText()
        samples = self._all_samples
        if mat_id is not None:
            samples = [s for s in samples if s.material_type_id == mat_id]
        if growth_filter == "Рост":
            samples = [s for s in samples if s.growth_flag == 1]
        elif growth_filter == "Нет роста":
            samples = [s for s in samples if s.growth_flag == 0]
        self._filtered = samples
        self._page = 0
        self._render_page()

    def _reset_filters(self) -> None:
        self.filter_mat.setCurrentIndex(0)
        self.filter_growth.setCurrentIndex(0)
        self._apply_filters()

    def _render_page(self) -> None:
        samples = self._filtered
        start = self._page * _PAGE_SIZE
        page_data = samples[start : start + _PAGE_SIZE]
        total_pages = max(1, (len(samples) + _PAGE_SIZE - 1) // _PAGE_SIZE)

        self.table.setRowCount(0)
        for s in page_data:
            r = self.table.rowCount()
            self.table.insertRow(r)
            taken = ""
            if getattr(s, "taken_at", None):
                try:
                    taken = s.taken_at.strftime("%d.%m.%Y")
                except Exception:
                    taken = str(s.taken_at)
            self.table.setItem(r, 0, QTableWidgetItem(str(s.id)))
            self.table.setItem(r, 1, QTableWidgetItem(str(s.patient_id)))
            self.table.setItem(r, 2, QTableWidgetItem(str(s.emr_case_id or "")))
            self.table.setItem(r, 3, QTableWidgetItem(s.lab_no))
            self.table.setItem(r, 4, QTableWidgetItem(getattr(s, "barcode", None) or ""))
            self.table.setItem(r, 5, QTableWidgetItem(taken))
            self.table.setItem(r, 6, QTableWidgetItem(s.material))
            self.table.setItem(r, 7, QTableWidgetItem(s.organism or ""))
            growth = {0: "Нет роста", 1: "Рост"}.get(s.growth_flag, "—")
            self.table.setItem(r, 8, QTableWidgetItem(growth))

        self.page_label.setText(f"Страница {self._page + 1} / {total_pages}")
        self.btn_prev.setEnabled(self._page > 0)
        self.btn_next.setEnabled(self._page < total_pages - 1)

    def _prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._render_page()

    def _next_page(self) -> None:
        total_pages = max(1, (len(self._filtered) + _PAGE_SIZE - 1) // _PAGE_SIZE)
        if self._page < total_pages - 1:
            self._page += 1
            self._render_page()

    def _open_detail(self, index) -> None:
        row = index.row()
        item = self.table.item(row, 0)
        if not item:
            return
        sample_id = int(item.text())
        dlg = LabSampleDetailDialog(sample_id, self._engine, self._session_ctx, parent=self)
        if dlg.exec():
            show_toast(self.window(), "Данные пробы сохранены.", "success")
            self.refresh()

    def _ask_patient_id(self) -> int | None:
        if self._context_patient_id is not None:
            return self._context_patient_id
        patient_id_raw, ok = QInputDialog.getText(self, "Новая проба", "patient_id:")
        if not ok:
            return None
        try:
            return int(patient_id_raw.strip())
        except ValueError:
            show_toast(self.window(), "patient_id должен быть числом.", "error")
            return None

    def create_auto_sample(self):
        patient_id = self._ask_patient_id()
        if patient_id is None:
            return
        try:
            self._svc.create_auto(
                patient_id=patient_id,
                emr_case_id=self._context_case_id,
                material="Кровь",
                organism=None,
            )
            show_toast(self.window(), "Проба создана с авто-номером.", "success")
            self.refresh()
        except Exception as exc:
            show_toast(self.window(), f"Ошибка: {exc}", "error")

    def create_manual_sample(self):
        patient_id = self._ask_patient_id()
        if patient_id is None:
            return
        lab_no, ok = QInputDialog.getText(self, "Новая проба", "lab_no (уникальный):")
        if not ok or not lab_no.strip():
            return
        try:
            self._svc.create(
                patient_id=patient_id,
                emr_case_id=self._context_case_id,
                lab_no=lab_no.strip(),
                material="Кровь",
                organism="",
                growth_flag=0,
                mic="",
                cfu="",
            )
            show_toast(self.window(), "Проба создана.", "success")
            self.refresh()
        except Exception as exc:
            show_toast(self.window(), f"Ошибка: {exc}", "error")
