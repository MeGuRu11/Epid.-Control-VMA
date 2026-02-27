"""Диалог карточки санитарной пробы: результаты + панели микробы/RIS/фаги."""
from __future__ import annotations

from typing import cast

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ...application.services.reference_service import ReferenceService
from ...application.services.sanitary_service import SanitaryService
from ..widgets.toast import show_toast

_RIS_OPTIONS = ["", "R", "I", "S"]


def _tbl(headers: list[str], max_height: int = 150) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    t.verticalHeader().setVisible(False)
    t.setAlternatingRowColors(True)
    t.setMaximumHeight(max_height)
    return t


class SanSampleDetailDialog(QDialog):
    def __init__(self, sample_id: int, engine, session_ctx, parent=None):
        super().__init__(parent)
        self.sample_id = sample_id
        self.svc = SanitaryService(engine, session_ctx)
        self.ref_svc = ReferenceService(engine, session_ctx)
        self._microbes: list = []
        self._antibiotics: list = []
        self._phages: list = []

        self.setWindowTitle(f"Санитарная проба #{sample_id}")
        self.setMinimumSize(680, 560)
        self.resize(760, 640)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        sample = self.svc.get_sample(sample_id)
        if sample:
            info = QLabel(
                f"<b>Lab №:</b> {sample.lab_no}  |  "
                f"<b>Точка отбора:</b> {sample.sampling_point}  |  "
                f"<b>Комната:</b> {sample.room or '—'}"
            )
            info.setWordWrap(True)
            layout.addWidget(info)

        # ── Результаты ────────────────────────────────────────────────────
        grp = QGroupBox("Результаты роста")
        form = QFormLayout(grp)
        form.setSpacing(6)

        self.growth_flag = QComboBox()
        self.growth_flag.addItem("Нет роста", 0)
        self.growth_flag.addItem("Рост", 1)
        if sample and sample.growth_flag is not None:
            self.growth_flag.setCurrentIndex(int(sample.growth_flag))

        self.colony_desc = QLineEdit(sample.colony_desc or "" if sample else "")
        self.colony_desc.setPlaceholderText("Описание колоний")
        self.microscopy = QLineEdit(sample.microscopy or "" if sample else "")
        self.microscopy.setPlaceholderText("Микроскопия")
        self.cfu = QLineEdit(sample.cfu or "" if sample else "")
        self.cfu.setPlaceholderText("КОЕ/мл")

        form.addRow("Рост:", self.growth_flag)
        form.addRow("Колонии:", self.colony_desc)
        form.addRow("Микроскопия:", self.microscopy)
        form.addRow("КОЕ/мл:", self.cfu)
        layout.addWidget(grp)

        # ── Изоляты ───────────────────────────────────────────────────────
        grp_iso = QGroupBox("Микробные изоляты")
        iso_l = QVBoxLayout(grp_iso)
        iso_l.setSpacing(4)
        self.tbl_iso = _tbl(["Микроорганизм", "Свободное поле", "Примечания"])
        iso_l.addWidget(self.tbl_iso)
        iso_btn = QHBoxLayout()
        b = QPushButton("+ Добавить")
        b.setObjectName("secondary")
        b.clicked.connect(self._iso_add)
        br = QPushButton("— Удалить")
        br.setObjectName("ghost")
        br.clicked.connect(lambda: self._remove_row(self.tbl_iso))
        iso_btn.addWidget(b)
        iso_btn.addWidget(br)
        iso_btn.addStretch(1)
        iso_l.addLayout(iso_btn)
        layout.addWidget(grp_iso)

        # ── RIS/MIC ───────────────────────────────────────────────────────
        grp_abx = QGroupBox("Чувствительность к АМП")
        abx_l = QVBoxLayout(grp_abx)
        abx_l.setSpacing(4)
        self.tbl_abx = _tbl(["Антибиотик", "RIS", "MIC (мг/л)", "Метод"])
        abx_l.addWidget(self.tbl_abx)
        abx_btn = QHBoxLayout()
        ba = QPushButton("+ Добавить")
        ba.setObjectName("secondary")
        ba.clicked.connect(self._abx_add)
        bar = QPushButton("— Удалить")
        bar.setObjectName("ghost")
        bar.clicked.connect(lambda: self._remove_row(self.tbl_abx))
        abx_btn.addWidget(ba)
        abx_btn.addWidget(bar)
        abx_btn.addStretch(1)
        abx_l.addLayout(abx_btn)
        layout.addWidget(grp_abx)

        # ── Фаги ──────────────────────────────────────────────────────────
        grp_ph = QGroupBox("Панель бактериофагов")
        ph_l = QVBoxLayout(grp_ph)
        ph_l.setSpacing(4)
        self.tbl_ph = _tbl(["Бактериофаг", "Свободное поле", "Диаметр лизиса (мм)"])
        ph_l.addWidget(self.tbl_ph)
        ph_btn = QHBoxLayout()
        bp = QPushButton("+ Добавить")
        bp.setObjectName("secondary")
        bp.clicked.connect(self._phage_add)
        bpr = QPushButton("— Удалить")
        bpr.setObjectName("ghost")
        bpr.clicked.connect(lambda: self._remove_row(self.tbl_ph))
        ph_btn.addWidget(bp)
        ph_btn.addWidget(bpr)
        ph_btn.addStretch(1)
        ph_l.addLayout(ph_btn)
        layout.addWidget(grp_ph)

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(self._save)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

        self._load_refs()
        self._load_panels()

    def _load_refs(self) -> None:
        try:
            self._microbes = self.ref_svc.microorganisms()
            self._antibiotics = self.ref_svc.antibiotics()
            self._phages = self.ref_svc.phages()
        except Exception:
            pass

    def _load_panels(self) -> None:
        try:
            panels = self.svc.get_panels(self.sample_id)
        except Exception:
            return
        for iso in panels.get("isolates", []):
            self._iso_add(microorganism_id=iso.microorganism_id, free=iso.microorganism_free or "", notes=iso.notes or "")
        for ab in panels.get("abx", []):
            self._abx_add(antibiotic_id=ab.antibiotic_id, ris=ab.ris or "", mic=str(ab.mic_mg_l) if ab.mic_mg_l else "", method=ab.method or "")
        for ph in panels.get("phages", []):
            self._phage_add(phage_id=ph.phage_id, free=ph.phage_free or "", diam=str(ph.lysis_diameter_mm) if ph.lysis_diameter_mm else "")

    def _iso_add(self, microorganism_id=None, free="", notes=""):
        r = self.tbl_iso.rowCount()
        self.tbl_iso.insertRow(r)
        combo = QComboBox()
        combo.addItem("— (своб. поле)", None)
        for m in self._microbes:
            combo.addItem(m.name, m.id)
        if microorganism_id is not None:
            for i in range(combo.count()):
                if combo.itemData(i) == microorganism_id:
                    combo.setCurrentIndex(i)
                    break
        self.tbl_iso.setCellWidget(r, 0, combo)
        self.tbl_iso.setItem(r, 1, QTableWidgetItem(free))
        self.tbl_iso.setItem(r, 2, QTableWidgetItem(notes))

    def _abx_add(self, antibiotic_id=None, ris="", mic="", method=""):
        r = self.tbl_abx.rowCount()
        self.tbl_abx.insertRow(r)
        combo = QComboBox()
        combo.addItem("— выбрать —", None)
        for a in self._antibiotics:
            combo.addItem(a.name, a.id)
        if antibiotic_id is not None:
            for i in range(combo.count()):
                if combo.itemData(i) == antibiotic_id:
                    combo.setCurrentIndex(i)
                    break
        ris_c = QComboBox()
        ris_c.addItems(_RIS_OPTIONS)
        ris_c.setCurrentText(ris)
        self.tbl_abx.setCellWidget(r, 0, combo)
        self.tbl_abx.setCellWidget(r, 1, ris_c)
        self.tbl_abx.setItem(r, 2, QTableWidgetItem(mic))
        self.tbl_abx.setItem(r, 3, QTableWidgetItem(method))

    def _phage_add(self, phage_id=None, free="", diam=""):
        r = self.tbl_ph.rowCount()
        self.tbl_ph.insertRow(r)
        combo = QComboBox()
        combo.addItem("— (своб. поле)", None)
        for p in self._phages:
            combo.addItem(p.name, p.id)
        if phage_id is not None:
            for i in range(combo.count()):
                if combo.itemData(i) == phage_id:
                    combo.setCurrentIndex(i)
                    break
        self.tbl_ph.setCellWidget(r, 0, combo)
        self.tbl_ph.setItem(r, 1, QTableWidgetItem(free))
        self.tbl_ph.setItem(r, 2, QTableWidgetItem(diam))

    def _remove_row(self, tbl: QTableWidget) -> None:
        rows = sorted({i.row() for i in tbl.selectedItems()}, reverse=True)
        for r in rows:
            tbl.removeRow(r)

    def _save(self) -> None:
        try:
            self.svc.update_result(self.sample_id, {
                "growth_flag": self.growth_flag.currentData(),
                "colony_desc": self.colony_desc.text().strip() or None,
                "microscopy": self.microscopy.text().strip() or None,
                "cfu": self.cfu.text().strip() or None,
            })

            isolates = []
            for r in range(self.tbl_iso.rowCount()):
                combo = cast(QComboBox, self.tbl_iso.cellWidget(r, 0))
                mid = combo.currentData() if combo else None
                free = (self.tbl_iso.item(r, 1) or QTableWidgetItem("")).text().strip() or None
                notes = (self.tbl_iso.item(r, 2) or QTableWidgetItem("")).text().strip() or None
                isolates.append({"microorganism_id": mid, "microorganism_free": free, "notes": notes})

            abx = []
            for r in range(self.tbl_abx.rowCount()):
                ac = cast(QComboBox, self.tbl_abx.cellWidget(r, 0))
                rc = cast(QComboBox, self.tbl_abx.cellWidget(r, 1))
                abx_id = ac.currentData() if ac else None
                ris = rc.currentText() if rc else ""
                mic_t = (self.tbl_abx.item(r, 2) or QTableWidgetItem("")).text().strip()
                method = (self.tbl_abx.item(r, 3) or QTableWidgetItem("")).text().strip() or None
                mic_v: float | None = None
                if mic_t:
                    try:
                        mic_v = float(mic_t.replace(",", "."))
                    except ValueError:
                        pass
                abx.append({"antibiotic_id": abx_id, "ris": ris or None, "mic_mg_l": mic_v, "method": method})

            phages = []
            for r in range(self.tbl_ph.rowCount()):
                pc = cast(QComboBox, self.tbl_ph.cellWidget(r, 0))
                ph_id = pc.currentData() if pc else None
                free = (self.tbl_ph.item(r, 1) or QTableWidgetItem("")).text().strip() or None
                d_t = (self.tbl_ph.item(r, 2) or QTableWidgetItem("")).text().strip()
                diam: float | None = None
                if d_t:
                    try:
                        diam = float(d_t.replace(",", "."))
                    except ValueError:
                        pass
                phages.append({"phage_id": ph_id, "phage_free": free, "lysis_diameter_mm": diam})

            self.svc.save_panels(self.sample_id, isolates=isolates, abx=abx, phages=phages)
            self.accept()
        except Exception as exc:
            show_toast(self.window(), f"Ошибка: {exc}", "error")
