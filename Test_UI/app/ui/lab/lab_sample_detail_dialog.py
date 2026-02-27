"""Диалог карточки лабораторной пробы: результаты роста + панели (микробы / RIS+MIC / фаги)."""
from __future__ import annotations

from typing import cast

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from ...application.services.lab_service import LabService
from ...application.services.reference_service import ReferenceService
from ..widgets.toast import show_toast

_RIS_OPTIONS = ["", "R", "I", "S"]


def _tbl(headers: list[str], max_height: int = 160) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    t.verticalHeader().setVisible(False)
    t.setAlternatingRowColors(True)
    t.setMaximumHeight(max_height)
    return t


class LabSampleDetailDialog(QDialog):
    def __init__(self, sample_id: int, engine, session_ctx, parent=None):
        super().__init__(parent)
        self.sample_id = sample_id
        self.svc = LabService(engine, session_ctx)
        self.ref_svc = ReferenceService(engine, session_ctx)
        self._microbes: list = []
        self._antibiotics: list = []
        self._phages: list = []

        self.setWindowTitle(f"Карточка пробы #{sample_id}")
        self.setMinimumSize(700, 600)
        self.resize(800, 680)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Заголовок ─────────────────────────────────────────────────────
        sample = self.svc.get_sample(sample_id)
        if sample:
            info = QLabel(
                f"<b>Lab №:</b> {sample.lab_no}  |  "
                f"<b>Материал:</b> {sample.material}  |  "
                f"<b>Patient ID:</b> {sample.patient_id}"
            )
            info.setWordWrap(True)
            layout.addWidget(info)

        # ── MDR/XDR баннер (скрыт до загрузки панелей) ───────────────────
        self._mdr_banner = QFrame()
        self._mdr_banner.setObjectName("mdrBanner")
        self._mdr_banner.setFixedHeight(36)
        mdr_lay = QHBoxLayout(self._mdr_banner)
        mdr_lay.setContentsMargins(12, 4, 12, 4)
        self._mdr_lbl = QLabel()
        self._mdr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mdr_lbl.setStyleSheet("font-size: 13px; font-weight: 700; background: transparent; border: none;")
        mdr_lay.addWidget(self._mdr_lbl)
        self._mdr_banner.hide()
        layout.addWidget(self._mdr_banner)

        # ── Результаты роста ──────────────────────────────────────────────
        grp_result = QGroupBox("Результаты роста")
        form = QFormLayout(grp_result)
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
        self.organism = QLineEdit(sample.organism or "" if sample else "")
        self.organism.setPlaceholderText("Микроорганизм (свободное поле)")

        # Barcode
        self.barcode = QLineEdit(getattr(sample, "barcode", None) or "" if sample else "")
        self.barcode.setPlaceholderText("Штрих-код пробы")

        # Дата результата
        self.result_date = QDateEdit()
        self.result_date.setCalendarPopup(True)
        self.result_date.setDisplayFormat("dd.MM.yyyy")
        self.result_date.setSpecialValueText("—")
        self.result_date.setMinimumDate(QDate(2000, 1, 1))
        result_dt = getattr(sample, "growth_result_at", None) if sample else None
        if result_dt:
            try:
                self.result_date.setDate(QDate(result_dt.year, result_dt.month, result_dt.day))
            except Exception:
                self.result_date.setDate(QDate.currentDate())
        else:
            self.result_date.setDate(QDate.currentDate())

        form.addRow("Рост:", self.growth_flag)
        form.addRow("Колонии:", self.colony_desc)
        form.addRow("Микроскопия:", self.microscopy)
        form.addRow("КОЕ/мл:", self.cfu)
        form.addRow("Организм:", self.organism)
        form.addRow("Barcode:", self.barcode)
        form.addRow("Дата результата:", self.result_date)
        layout.addWidget(grp_result)

        # ── Изоляты микробов ──────────────────────────────────────────────
        grp_iso = QGroupBox("Микробные изоляты")
        iso_lay = QVBoxLayout(grp_iso)
        iso_lay.setSpacing(4)
        self.tbl_iso = _tbl(["Микроорганизм (справочник)", "Свободное поле", "Примечания"])
        iso_lay.addWidget(self.tbl_iso)
        iso_btn = QHBoxLayout()
        btn_iso_add = QPushButton("+ Добавить")
        btn_iso_add.setObjectName("secondary")
        btn_iso_add.clicked.connect(self._iso_add)
        btn_iso_rem = QPushButton("— Удалить")
        btn_iso_rem.setObjectName("ghost")
        btn_iso_rem.clicked.connect(lambda: self._remove_row(self.tbl_iso))
        iso_btn.addWidget(btn_iso_add)
        iso_btn.addWidget(btn_iso_rem)
        iso_btn.addStretch(1)
        iso_lay.addLayout(iso_btn)
        layout.addWidget(grp_iso)

        # ── RIS/MIC панель ────────────────────────────────────────────────
        grp_abx = QGroupBox("Чувствительность к АМП (RIS/MIC)")
        abx_lay = QVBoxLayout(grp_abx)
        abx_lay.setSpacing(4)
        self.tbl_abx = _tbl(["Антибиотик", "RIS", "MIC (мг/л)", "Метод"])
        abx_lay.addWidget(self.tbl_abx)
        abx_btn = QHBoxLayout()
        btn_abx_add = QPushButton("+ Добавить")
        btn_abx_add.setObjectName("secondary")
        btn_abx_add.clicked.connect(self._abx_add)
        btn_abx_rem = QPushButton("— Удалить")
        btn_abx_rem.setObjectName("ghost")
        btn_abx_rem.clicked.connect(lambda: self._remove_row(self.tbl_abx))
        abx_btn.addWidget(btn_abx_add)
        abx_btn.addWidget(btn_abx_rem)
        abx_btn.addStretch(1)
        abx_lay.addLayout(abx_btn)
        layout.addWidget(grp_abx)

        # ── Панель фагов ──────────────────────────────────────────────────
        grp_phage = QGroupBox("Панель бактериофагов")
        phage_lay = QVBoxLayout(grp_phage)
        phage_lay.setSpacing(4)
        self.tbl_phage = _tbl(["Бактериофаг (справочник)", "Свободное поле", "Диаметр лизиса (мм)"])
        phage_lay.addWidget(self.tbl_phage)
        phage_btn = QHBoxLayout()
        btn_phage_add = QPushButton("+ Добавить")
        btn_phage_add.setObjectName("secondary")
        btn_phage_add.clicked.connect(self._phage_add)
        btn_phage_rem = QPushButton("— Удалить")
        btn_phage_rem.setObjectName("ghost")
        btn_phage_rem.clicked.connect(lambda: self._remove_row(self.tbl_phage))
        phage_btn.addWidget(btn_phage_add)
        phage_btn.addWidget(btn_phage_rem)
        phage_btn.addStretch(1)
        phage_lay.addLayout(phage_btn)
        layout.addWidget(grp_phage)

        # ── Кнопки диалога ────────────────────────────────────────────────
        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(self._save)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

        # ── Загрузка данных ───────────────────────────────────────────────
        self._load_refs()
        self._load_panels()

    # ── Refs ──────────────────────────────────────────────────────────────
    def _load_refs(self) -> None:
        try:
            self._microbes = self.ref_svc.microorganisms()
            self._antibiotics = self.ref_svc.antibiotics()
            self._phages = self.ref_svc.phages()
        except Exception:
            pass

    # ── Load existing panels ──────────────────────────────────────────────
    def _load_panels(self) -> None:
        try:
            panels = self.svc.get_panels(self.sample_id)
        except Exception:
            return

        for iso in panels.get("isolates", []):
            self._iso_add(microorganism_id=iso.microorganism_id, free=iso.microorganism_free or "", notes=iso.notes or "")

        abx_list = panels.get("abx", [])
        for ab in abx_list:
            self._abx_add(antibiotic_id=ab.antibiotic_id, ris=ab.ris or "", mic=str(ab.mic_mg_l) if ab.mic_mg_l else "", method=ab.method or "")

        for ph in panels.get("phages", []):
            self._phage_add(phage_id=ph.phage_id, free=ph.phage_free or "", diam=str(ph.lysis_diameter_mm) if ph.lysis_diameter_mm else "")

        self._update_mdr_banner(abx_list)

    # ── MDR/XDR detection ─────────────────────────────────────────────────
    def _update_mdr_banner(self, abx_panels: list) -> None:
        r_groups = {
            getattr(p, "group_id", None)
            for p in abx_panels
            if (getattr(p, "ris", "") or "").upper() == "R" and getattr(p, "group_id", None)
        }
        n = len(r_groups)
        if n >= 5:
            profile = "XDR"
            style = (
                "background: #FDEDEC; border: 1px solid #E74C3C; border-radius: 8px;"
            )
            self._mdr_lbl.setText("🔴  XDR-патоген — требуется уведомление эпидемиолога")
            self._mdr_lbl.setStyleSheet(
                "font-size: 13px; font-weight: 700; color: #922B21; background: transparent; border: none;"
            )
        elif n >= 3:
            profile = "MDR"
            style = (
                "background: #FEF9E7; border: 1px solid #F1C40F; border-radius: 8px;"
            )
            self._mdr_lbl.setText("⚠  MDR-патоген")
            self._mdr_lbl.setStyleSheet(
                "font-size: 13px; font-weight: 700; color: #7D6608; background: transparent; border: none;"
            )
        else:
            self._mdr_banner.hide()
            return
        self._mdr_banner.setStyleSheet(f"QFrame#mdrBanner {{ {style} }}")
        self._mdr_banner.show()

    # ── Isolates ──────────────────────────────────────────────────────────
    def _iso_add(self, microorganism_id: int | None = None, free: str = "", notes: str = "") -> None:
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

    # ── ABx ───────────────────────────────────────────────────────────────
    def _abx_add(self, antibiotic_id: int | None = None, ris: str = "", mic: str = "", method: str = "") -> None:
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
        ris_combo = QComboBox()
        ris_combo.addItems(_RIS_OPTIONS)
        ris_combo.setCurrentText(ris)
        self.tbl_abx.setCellWidget(r, 0, combo)
        self.tbl_abx.setCellWidget(r, 1, ris_combo)
        self.tbl_abx.setItem(r, 2, QTableWidgetItem(mic))
        self.tbl_abx.setItem(r, 3, QTableWidgetItem(method))

    # ── Phages ────────────────────────────────────────────────────────────
    def _phage_add(self, phage_id: int | None = None, free: str = "", diam: str = "") -> None:
        r = self.tbl_phage.rowCount()
        self.tbl_phage.insertRow(r)
        combo = QComboBox()
        combo.addItem("— (своб. поле)", None)
        for p in self._phages:
            combo.addItem(p.name, p.id)
        if phage_id is not None:
            for i in range(combo.count()):
                if combo.itemData(i) == phage_id:
                    combo.setCurrentIndex(i)
                    break
        self.tbl_phage.setCellWidget(r, 0, combo)
        self.tbl_phage.setItem(r, 1, QTableWidgetItem(free))
        self.tbl_phage.setItem(r, 2, QTableWidgetItem(diam))

    # ── Common ────────────────────────────────────────────────────────────
    def _remove_row(self, tbl: QTableWidget) -> None:
        rows = sorted({i.row() for i in tbl.selectedItems()}, reverse=True)
        for r in rows:
            tbl.removeRow(r)

    # ── Save ──────────────────────────────────────────────────────────────
    def _save(self) -> None:
        try:
            # Парсим дату результата
            from datetime import datetime
            qd = self.result_date.date()
            try:
                result_dt = datetime(qd.year(), qd.month(), qd.day())
            except Exception:
                result_dt = None

            # Основные результаты
            self.svc.update_result(
                self.sample_id,
                {
                    "growth_flag": self.growth_flag.currentData(),
                    "colony_desc": self.colony_desc.text().strip() or None,
                    "microscopy": self.microscopy.text().strip() or None,
                    "cfu": self.cfu.text().strip() or None,
                    "organism": self.organism.text().strip() or None,
                    "barcode": self.barcode.text().strip() or None,
                    "growth_result_at": result_dt,
                },
            )

            # Изоляты
            isolates = []
            for r in range(self.tbl_iso.rowCount()):
                combo = cast(QComboBox, self.tbl_iso.cellWidget(r, 0))
                mid = combo.currentData() if combo else None
                free = (self.tbl_iso.item(r, 1) or QTableWidgetItem("")).text().strip() or None
                notes = (self.tbl_iso.item(r, 2) or QTableWidgetItem("")).text().strip() or None
                isolates.append({"microorganism_id": mid, "microorganism_free": free, "notes": notes})

            # ABx
            abx = []
            for r in range(self.tbl_abx.rowCount()):
                abx_combo = cast(QComboBox, self.tbl_abx.cellWidget(r, 0))
                ris_combo = cast(QComboBox, self.tbl_abx.cellWidget(r, 1))
                abx_id = abx_combo.currentData() if abx_combo else None
                ris_val = ris_combo.currentText() if ris_combo else ""
                mic_text = (self.tbl_abx.item(r, 2) or QTableWidgetItem("")).text().strip()
                method = (self.tbl_abx.item(r, 3) or QTableWidgetItem("")).text().strip() or None
                mic_val: float | None = None
                if mic_text:
                    try:
                        mic_val = float(mic_text.replace(",", "."))
                    except ValueError:
                        pass
                abx.append({"antibiotic_id": abx_id, "ris": ris_val or None, "mic_mg_l": mic_val, "method": method})

            # Фаги
            phages = []
            for r in range(self.tbl_phage.rowCount()):
                ph_combo = cast(QComboBox, self.tbl_phage.cellWidget(r, 0))
                ph_id = ph_combo.currentData() if ph_combo else None
                free = (self.tbl_phage.item(r, 1) or QTableWidgetItem("")).text().strip() or None
                diam_text = (self.tbl_phage.item(r, 2) or QTableWidgetItem("")).text().strip()
                diam: float | None = None
                if diam_text:
                    try:
                        diam = float(diam_text.replace(",", "."))
                    except ValueError:
                        pass
                phages.append({"phage_id": ph_id, "phage_free": free, "lysis_diameter_mm": diam})

            self.svc.save_panels(self.sample_id, isolates=isolates, abx=abx, phages=phages)
            self.accept()
        except Exception as exc:
            show_toast(self.window(), f"Ошибка сохранения: {exc}", "error")
