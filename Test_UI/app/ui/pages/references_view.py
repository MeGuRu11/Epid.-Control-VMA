from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...application.services.reference_service import ReferenceService
from ..widgets.toast import show_toast


def _tbl(headers: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    t.setAlternatingRowColors(True)
    t.horizontalHeader().setStretchLastSection(True)
    t.verticalHeader().setVisible(False)
    return t


class _SearchBar(QWidget):
    def __init__(self, placeholder: str = "Поиск...", parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.btn = QPushButton("Найти")
        self.btn.setObjectName("secondary")
        row.addWidget(self.edit, 1)
        row.addWidget(self.btn)


# ─────────────────────────────────────────────────────────────────────────────
class _DepartmentsTab(QWidget):
    def __init__(self, svc: ReferenceService, is_admin: bool):
        super().__init__()
        self.svc = svc
        self.is_admin = is_admin
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        self.tbl = _tbl(["ID", "Название"])
        layout.addWidget(self.tbl)
        if is_admin:
            btn_row = QHBoxLayout()
            btn = QPushButton("+ Добавить отделение")
            btn.clicked.connect(self._add)
            btn_row.addWidget(btn)
            btn_row.addStretch(1)
            layout.addLayout(btn_row)
        self.refresh()

    def refresh(self):
        rows = self.svc.departments()
        self.tbl.setRowCount(0)
        for dep in rows:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(str(dep.id)))
            self.tbl.setItem(r, 1, QTableWidgetItem(dep.name))

    def _add(self):
        name, ok = QInputDialog.getText(self, "Новое отделение", "Название:")
        if not ok or not name.strip():
            return
        try:
            self.svc.create_department(name.strip())
            self.refresh()
            show_toast(self.window(), "Отделение добавлено.", "success")
        except Exception as exc:
            show_toast(self.window(), str(exc), "error")


# ─────────────────────────────────────────────────────────────────────────────
class _MaterialTypesTab(QWidget):
    def __init__(self, svc: ReferenceService, is_admin: bool):
        super().__init__()
        self.svc = svc
        self.is_admin = is_admin
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        self.tbl = _tbl(["ID", "Код", "Название"])
        layout.addWidget(self.tbl)
        if is_admin:
            btn_row = QHBoxLayout()
            btn = QPushButton("+ Добавить вид материала")
            btn.clicked.connect(self._add)
            btn_row.addWidget(btn)
            btn_row.addStretch(1)
            layout.addLayout(btn_row)
        self.refresh()

    def refresh(self):
        rows = self.svc.material_types()
        self.tbl.setRowCount(0)
        for mt in rows:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(str(mt.id)))
            self.tbl.setItem(r, 1, QTableWidgetItem(mt.code))
            self.tbl.setItem(r, 2, QTableWidgetItem(mt.name))

    def _add(self):
        code, ok = QInputDialog.getText(self, "Новый вид материала", "Код (лат., макс. 10 симв.):")
        if not ok or not code.strip():
            return
        name, ok2 = QInputDialog.getText(self, "Новый вид материала", "Название:")
        if not ok2 or not name.strip():
            return
        try:
            self.svc.create_material_type(code.strip(), name.strip())
            self.refresh()
            show_toast(self.window(), "Вид материала добавлен.", "success")
        except Exception as exc:
            show_toast(self.window(), str(exc), "error")


# ─────────────────────────────────────────────────────────────────────────────
class _Icd10Tab(QWidget):
    def __init__(self, svc: ReferenceService, is_admin: bool):
        super().__init__()
        self.svc = svc
        self.is_admin = is_admin
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        self.search = _SearchBar("Поиск по коду или названию...")
        self.search.btn.clicked.connect(self.refresh)
        self.search.edit.returnPressed.connect(self.refresh)
        layout.addWidget(self.search)
        self.tbl = _tbl(["Код", "Название", "Активен"])
        layout.addWidget(self.tbl)
        if is_admin:
            btn_row = QHBoxLayout()
            btn_add = QPushButton("+ Добавить МКБ-10")
            btn_add.clicked.connect(self._add)
            btn_toggle = QPushButton("Вкл/Выкл активность")
            btn_toggle.setObjectName("secondary")
            btn_toggle.clicked.connect(self._toggle)
            btn_row.addWidget(btn_add)
            btn_row.addWidget(btn_toggle)
            btn_row.addStretch(1)
            layout.addLayout(btn_row)
        self.refresh()

    def refresh(self):
        q = self.search.edit.text().strip()
        rows = self.svc.icd10_list(q=q)
        self.tbl.setRowCount(0)
        for rec in rows:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(rec.code))
            self.tbl.setItem(r, 1, QTableWidgetItem(rec.title))
            self.tbl.setItem(r, 2, QTableWidgetItem("Да" if rec.is_active else "Нет"))

    def _add(self):
        code, ok = QInputDialog.getText(self, "Добавить МКБ-10", "Код (напр. A41.9):")
        if not ok or not code.strip():
            return
        title, ok2 = QInputDialog.getText(self, "Добавить МКБ-10", "Название:")
        if not ok2 or not title.strip():
            return
        try:
            self.svc.create_icd10(code.strip(), title.strip())
            self.refresh()
            show_toast(self.window(), "МКБ-10 добавлен.", "success")
        except Exception as exc:
            show_toast(self.window(), str(exc), "error")

    def _toggle(self):
        if not self.tbl.selectedItems():
            return
        row = self.tbl.currentRow()
        code = (self.tbl.item(row, 0) or QTableWidgetItem("")).text()
        active_text = (self.tbl.item(row, 2) or QTableWidgetItem("")).text()
        try:
            self.svc.set_icd10_active(code, active_text != "Да")
            self.refresh()
        except Exception as exc:
            show_toast(self.window(), str(exc), "error")


# ─────────────────────────────────────────────────────────────────────────────
class _MicroorganismsTab(QWidget):
    def __init__(self, svc: ReferenceService, is_admin: bool):
        super().__init__()
        self.svc = svc
        self.is_admin = is_admin
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        self.search = _SearchBar("Поиск по названию...")
        self.search.btn.clicked.connect(self.refresh)
        self.search.edit.returnPressed.connect(self.refresh)
        layout.addWidget(self.search)
        self.tbl = _tbl(["ID", "Код", "Название", "Таксон-группа", "Активен"])
        layout.addWidget(self.tbl)
        if is_admin:
            btn_row = QHBoxLayout()
            btn_add = QPushButton("+ Добавить микроорганизм")
            btn_add.clicked.connect(self._add)
            btn_toggle = QPushButton("Вкл/Выкл активность")
            btn_toggle.setObjectName("secondary")
            btn_toggle.clicked.connect(self._toggle)
            btn_row.addWidget(btn_add)
            btn_row.addWidget(btn_toggle)
            btn_row.addStretch(1)
            layout.addLayout(btn_row)
        self.refresh()

    def refresh(self):
        q = self.search.edit.text().strip()
        rows = self.svc.microorganisms(q=q)
        self.tbl.setRowCount(0)
        for rec in rows:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(str(rec.id)))
            self.tbl.setItem(r, 1, QTableWidgetItem(rec.code or ""))
            self.tbl.setItem(r, 2, QTableWidgetItem(rec.name))
            self.tbl.setItem(r, 3, QTableWidgetItem(rec.taxon_group or ""))
            self.tbl.setItem(r, 4, QTableWidgetItem("Да" if rec.is_active else "Нет"))

    def _add(self):
        name, ok = QInputDialog.getText(self, "Добавить микроорганизм", "Название:")
        if not ok or not name.strip():
            return
        code, _ = QInputDialog.getText(self, "Добавить микроорганизм", "Код (необязательно):")
        taxon, _ = QInputDialog.getText(self, "Добавить микроорганизм", "Таксон-группа (необязательно):")
        try:
            self.svc.create_microorganism(code, name.strip(), taxon)
            self.refresh()
            show_toast(self.window(), "Микроорганизм добавлен.", "success")
        except Exception as exc:
            show_toast(self.window(), str(exc), "error")

    def _toggle(self):
        if not self.tbl.selectedItems():
            return
        row = self.tbl.currentRow()
        org_id = int((self.tbl.item(row, 0) or QTableWidgetItem("0")).text())
        active_text = (self.tbl.item(row, 4) or QTableWidgetItem("")).text()
        try:
            self.svc.set_microorganism_active(org_id, active_text != "Да")
            self.refresh()
        except Exception as exc:
            show_toast(self.window(), str(exc), "error")


# ─────────────────────────────────────────────────────────────────────────────
class _AbxGroupsTab(QWidget):
    def __init__(self, svc: ReferenceService, is_admin: bool):
        super().__init__()
        self.svc = svc
        self.is_admin = is_admin
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        self.tbl = _tbl(["ID", "Код", "Название"])
        layout.addWidget(self.tbl)
        if is_admin:
            btn_row = QHBoxLayout()
            btn = QPushButton("+ Добавить группу АБ")
            btn.clicked.connect(self._add)
            btn_row.addWidget(btn)
            btn_row.addStretch(1)
            layout.addLayout(btn_row)
        self.refresh()

    def refresh(self):
        rows = self.svc.antibiotic_groups()
        self.tbl.setRowCount(0)
        for rec in rows:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(str(rec.id)))
            self.tbl.setItem(r, 1, QTableWidgetItem(rec.code or ""))
            self.tbl.setItem(r, 2, QTableWidgetItem(rec.name))

    def _add(self):
        name, ok = QInputDialog.getText(self, "Добавить группу АБ", "Название:")
        if not ok or not name.strip():
            return
        code, _ = QInputDialog.getText(self, "Добавить группу АБ", "Код (необязательно):")
        try:
            self.svc.create_antibiotic_group(code, name.strip())
            self.refresh()
            show_toast(self.window(), "Группа антибиотиков добавлена.", "success")
        except Exception as exc:
            show_toast(self.window(), str(exc), "error")


# ─────────────────────────────────────────────────────────────────────────────
class _AntibioticsTab(QWidget):
    def __init__(self, svc: ReferenceService, is_admin: bool):
        super().__init__()
        self.svc = svc
        self.is_admin = is_admin
        self._groups: list = []
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        self.tbl = _tbl(["ID", "Код", "Название", "Группа"])
        layout.addWidget(self.tbl)
        if is_admin:
            btn_row = QHBoxLayout()
            btn = QPushButton("+ Добавить антибиотик")
            btn.clicked.connect(self._add)
            btn_row.addWidget(btn)
            btn_row.addStretch(1)
            layout.addLayout(btn_row)
        self.refresh()

    def refresh(self):
        self._groups = self.svc.antibiotic_groups()
        grp_map = {g.id: g.name for g in self._groups}
        rows = self.svc.antibiotics()
        self.tbl.setRowCount(0)
        for rec in rows:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(str(rec.id)))
            self.tbl.setItem(r, 1, QTableWidgetItem(rec.code or ""))
            self.tbl.setItem(r, 2, QTableWidgetItem(rec.name))
            self.tbl.setItem(r, 3, QTableWidgetItem(grp_map.get(rec.group_id, "") if rec.group_id else ""))

    def _add(self):
        name, ok = QInputDialog.getText(self, "Добавить антибиотик", "Название:")
        if not ok or not name.strip():
            return
        code, _ = QInputDialog.getText(self, "Добавить антибиотик", "Код (необязательно):")
        grp_names = ["— (без группы)"] + [g.name for g in self._groups]
        grp_sel, ok2 = QInputDialog.getItem(self, "Добавить антибиотик", "Группа:", grp_names, 0, False)
        if not ok2:
            return
        group_id: int | None = None
        for g in self._groups:
            if g.name == grp_sel:
                group_id = g.id
                break
        try:
            self.svc.create_antibiotic(code, name.strip(), group_id)
            self.refresh()
            show_toast(self.window(), "Антибиотик добавлен.", "success")
        except Exception as exc:
            show_toast(self.window(), str(exc), "error")


# ─────────────────────────────────────────────────────────────────────────────
class _PhagesTab(QWidget):
    def __init__(self, svc: ReferenceService, is_admin: bool):
        super().__init__()
        self.svc = svc
        self.is_admin = is_admin
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        self.tbl = _tbl(["ID", "Код", "Название", "Активен"])
        layout.addWidget(self.tbl)
        if is_admin:
            btn_row = QHBoxLayout()
            btn_add = QPushButton("+ Добавить фаг")
            btn_add.clicked.connect(self._add)
            btn_toggle = QPushButton("Вкл/Выкл активность")
            btn_toggle.setObjectName("secondary")
            btn_toggle.clicked.connect(self._toggle)
            btn_row.addWidget(btn_add)
            btn_row.addWidget(btn_toggle)
            btn_row.addStretch(1)
            layout.addLayout(btn_row)
        self.refresh()

    def refresh(self):
        rows = self.svc.phages()
        self.tbl.setRowCount(0)
        for rec in rows:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(str(rec.id)))
            self.tbl.setItem(r, 1, QTableWidgetItem(rec.code or ""))
            self.tbl.setItem(r, 2, QTableWidgetItem(rec.name))
            self.tbl.setItem(r, 3, QTableWidgetItem("Да" if rec.is_active else "Нет"))

    def _add(self):
        name, ok = QInputDialog.getText(self, "Добавить фаг", "Название:")
        if not ok or not name.strip():
            return
        code, _ = QInputDialog.getText(self, "Добавить фаг", "Код (необязательно):")
        try:
            self.svc.create_phage(code, name.strip())
            self.refresh()
            show_toast(self.window(), "Бактериофаг добавлен.", "success")
        except Exception as exc:
            show_toast(self.window(), str(exc), "error")

    def _toggle(self):
        if not self.tbl.selectedItems():
            return
        row = self.tbl.currentRow()
        phage_id = int((self.tbl.item(row, 0) or QTableWidgetItem("0")).text())
        active_text = (self.tbl.item(row, 3) or QTableWidgetItem("")).text()
        try:
            self.svc.set_phage_active(phage_id, active_text != "Да")
            self.refresh()
        except Exception as exc:
            show_toast(self.window(), str(exc), "error")


# ─────────────────────────────────────────────────────────────────────────────
class ReferencesView(QWidget):
    def __init__(self, engine, session_ctx):
        super().__init__()
        self._session = session_ctx
        self._svc = ReferenceService(engine, session_ctx)
        is_admin = session_ctx.role == "admin"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("Справочники (НСИ)")
        title.setObjectName("title")
        head.addWidget(title, 1)
        btn_refresh = QPushButton("Обновить всё")
        btn_refresh.setObjectName("secondary")
        btn_refresh.clicked.connect(self.refresh)
        head.addWidget(btn_refresh)
        layout.addLayout(head)

        if not is_admin:
            note = QLabel("Режим просмотра. Для изменений требуется роль admin.")
            note.setObjectName("muted")
            layout.addWidget(note)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        self._dep_tab = _DepartmentsTab(self._svc, is_admin)
        self._mat_tab = _MaterialTypesTab(self._svc, is_admin)
        self._icd_tab = _Icd10Tab(self._svc, is_admin)
        self._micro_tab = _MicroorganismsTab(self._svc, is_admin)
        self._abxgrp_tab = _AbxGroupsTab(self._svc, is_admin)
        self._abx_tab = _AntibioticsTab(self._svc, is_admin)
        self._phage_tab = _PhagesTab(self._svc, is_admin)

        self.tabs.addTab(self._dep_tab, "Отделения")
        self.tabs.addTab(self._mat_tab, "Виды материалов")
        self.tabs.addTab(self._icd_tab, "МКБ-10")
        self.tabs.addTab(self._micro_tab, "Микроорганизмы")
        self.tabs.addTab(self._abxgrp_tab, "Группы АБ")
        self.tabs.addTab(self._abx_tab, "Антибиотики")
        self.tabs.addTab(self._phage_tab, "Бактериофаги")

    def refresh(self):
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if hasattr(w, "refresh"):
                w.refresh()
        show_toast(self.window(), "Справочники обновлены.", "info")
