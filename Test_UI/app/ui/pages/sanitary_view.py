from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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

from ...application.services.reference_service import ReferenceService
from ...application.services.sanitary_service import SanitaryService
from ..sanitary.san_sample_detail_dialog import SanSampleDetailDialog
from ..widgets.toast import show_toast


class SanitaryView(QWidget):
    def __init__(self, engine, session_ctx):
        super().__init__()
        self._engine = engine
        self._session_ctx = session_ctx
        self._svc = SanitaryService(engine, session_ctx)
        self._ref_svc = ReferenceService(engine, session_ctx)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Санитарная микробиология")
        title.setObjectName("title")
        layout.addWidget(title)

        # ── Фильтр по отделению ───────────────────────────────────────────
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Отделение:"))
        self.filter_dep = QComboBox()
        self.filter_dep.setMinimumWidth(160)
        filter_row.addWidget(self.filter_dep)
        btn_apply = QPushButton("Применить")
        btn_apply.setObjectName("secondary")
        btn_apply.clicked.connect(self.refresh)
        btn_reset = QPushButton("Сброс")
        btn_reset.setObjectName("ghost")
        btn_reset.clicked.connect(self._reset_filter)
        filter_row.addWidget(btn_apply)
        filter_row.addWidget(btn_reset)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        # ── Действия ──────────────────────────────────────────────────────
        actions = QHBoxLayout()
        btn_new = QPushButton("Новая санитарная проба")
        btn_new.clicked.connect(self.create_sample)
        btn_refresh = QPushButton("Обновить")
        btn_refresh.setObjectName("secondary")
        btn_refresh.clicked.connect(self.refresh)
        actions.addWidget(btn_new)
        actions.addWidget(btn_refresh)
        actions.addStretch(1)
        layout.addLayout(actions)

        # ── Таблица ───────────────────────────────────────────────────────
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Lab №", "Отдел. ID", "Точка отбора", "Комната", "CFU"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.doubleClicked.connect(self._open_detail)
        layout.addWidget(self.table, 1)

        hint = QLabel("Двойной клик — открыть карточку санпробы")
        hint.setObjectName("muted")
        layout.addWidget(hint)

        self._load_departments()
        self.refresh()

    def _load_departments(self) -> None:
        self.filter_dep.clear()
        self.filter_dep.addItem("Все отделения", None)
        try:
            for dep in self._ref_svc.departments():
                self.filter_dep.addItem(dep.name, dep.id)
        except Exception:
            pass

    def _reset_filter(self) -> None:
        self.filter_dep.setCurrentIndex(0)
        self.refresh()

    def refresh(self):
        dep_id = self.filter_dep.currentData()
        rows = self._svc.list(department_id=dep_id)
        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(row.id)))
            self.table.setItem(r, 1, QTableWidgetItem(row.lab_no))
            self.table.setItem(r, 2, QTableWidgetItem(str(row.department_id or "")))
            self.table.setItem(r, 3, QTableWidgetItem(row.sampling_point))
            self.table.setItem(r, 4, QTableWidgetItem(row.room or ""))
            self.table.setItem(r, 5, QTableWidgetItem(row.cfu or ""))

    def _open_detail(self, index) -> None:
        row = index.row()
        item = self.table.item(row, 0)
        if not item:
            return
        sample_id = int(item.text())
        dlg = SanSampleDetailDialog(sample_id, self._engine, self._session_ctx, parent=self)
        if dlg.exec():
            show_toast(self.window(), "Данные санпробы сохранены.", "success")
            self.refresh()

    def create_sample(self):
        point, ok = QInputDialog.getText(self, "Санитарная проба", "Точка отбора:")
        if not ok or not point.strip():
            return
        room, ok = QInputDialog.getText(self, "Санитарная проба", "Комната (необязательно):")
        if not ok:
            return
        cfu, ok = QInputDialog.getText(self, "Санитарная проба", "КОЕ/мл (необязательно):")
        if not ok:
            return
        try:
            self._svc.create_auto(
                sampling_point=point.strip(),
                room=room.strip() or None,
                cfu=cfu.strip() or None,
            )
            show_toast(self.window(), "Санитарная проба создана.", "success")
            self.refresh()
        except Exception as exc:
            show_toast(self.window(), f"Ошибка: {exc}", "error")
