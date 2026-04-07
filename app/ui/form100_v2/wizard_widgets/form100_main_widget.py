"""Form100MainWidget вЂ” С†РµРЅС‚СЂР°Р»СЊРЅР°СЏ С‡Р°СЃС‚СЊ Р±Р»Р°РЅРєР° Р¤РѕСЂРјС‹ 100."""
from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QDate, Qt, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.form100_v2.wizard_widgets.bodymap_widget import BodyMapWidget
from app.ui.form100_v2.wizard_widgets.lesion_type_widget import LesionTypeWidget

LESION_ITEMS: tuple[tuple[str, str], ...] = (
    ("lesion_gunshot",    "Рћ  РћРіРЅРµСЃС‚СЂРµР»СЊРЅРѕРµ"),
    ("lesion_nuclear",    "РЇ  РЇРґРµСЂРЅРѕРµ"),
    ("lesion_chemical",   "РҐ  РҐРёРјРёС‡РµСЃРєРѕРµ"),
    ("lesion_biological", "Р‘Р°Рє. Р‘Р°РєС‚РµСЂРёРѕР»."),
    ("lesion_other",      "Р”СЂСѓРіРёРµ"),
    ("lesion_frostbite",  "РћС‚Рј. РћС‚РјРѕСЂРѕР¶РµРЅРёРµ"),
    ("lesion_burn",       "Р‘  РћР¶РѕРі"),
    ("lesion_misc",       "Р  РРЅРѕРµ"),
)

SAN_LOSS_ITEMS: tuple[tuple[str, str], ...] = (
    ("san_loss_gunshot",    "Рћ  РћРіРЅРµСЃС‚СЂРµР»СЊРЅРѕРµ"),
    ("san_loss_nuclear",    "РЇ  РЇРґРµСЂРЅРѕРµ"),
    ("san_loss_chemical",   "РҐ  РҐРёРјРёС‡РµСЃРєРѕРµ"),
    ("san_loss_biological", "Р‘Р°Рє. Р‘Р°РєС‚РµСЂРёРѕР»."),
    ("san_loss_other",      "Р”СЂСѓРіРёРµ"),
    ("san_loss_frostbite",  "РћС‚Рј. РћС‚РјРѕСЂРѕР¶РµРЅРёРµ"),
    ("san_loss_burn",       "Р‘  РћР¶РѕРі"),
    ("san_loss_misc",       "Р  РРЅРѕРµ"),
)

TISSUE_TYPES: tuple[str, ...] = (
    "РјСЏРіРєРёРµ С‚РєР°РЅРё",
    "РєРѕСЃС‚Рё",
    "СЃРѕСЃСѓРґС‹",
    "РїРѕР»РѕСЃС‚РЅС‹Рµ СЂР°РЅС‹",
    "РѕР¶РѕРіРё",
)


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Form100MainWidget(QWidget):
    """РћСЃРЅРѕРІРЅРѕР№ Р±Р»Р°РЅРє Р¤РѕСЂРјС‹ 100: РїРѕСЂР°Р¶РµРЅРёСЏ + СЃС…РµРјР° С‚РµР»Р° + РјРµРґРёС†РёРЅСЃРєР°СЏ РїРѕРјРѕС‰СЊ + РёРґРµРЅС‚РёС„РёРєР°С†РёСЏ."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        root.addLayout(top_row, 1)

        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(6)

        lesion_box = QGroupBox("Р’РёРґ РїРѕСЂР°Р¶РµРЅРёСЏ")
        lesion_box.setObjectName("form100Lesion")
        lesion_lay = QVBoxLayout(lesion_box)
        lesion_lay.setContentsMargins(8, 6, 8, 6)
        self.lesion_widget = LesionTypeWidget(LESION_ITEMS)
        lesion_lay.addWidget(self.lesion_widget)
        left_col.addWidget(lesion_box)

        san_box = QGroupBox("Р’РёРґ СЃР°РЅ. РїРѕС‚РµСЂСЊ")
        san_box.setObjectName("form100Lesion")
        san_lay = QVBoxLayout(san_box)
        san_lay.setContentsMargins(8, 6, 8, 6)
        self.san_loss_widget = LesionTypeWidget(SAN_LOSS_ITEMS)
        san_lay.addWidget(self.san_loss_widget)
        left_col.addWidget(san_box)

        tissue_box = QGroupBox("РўРёРїС‹ С‚РєР°РЅРµР№")
        tissue_box.setObjectName("form100Tissue")
        tissue_lay = QGridLayout(tissue_box)
        tissue_lay.setContentsMargins(8, 6, 8, 6)
        tissue_lay.setHorizontalSpacing(8)
        tissue_lay.setVerticalSpacing(4)
        self.chk_tissues: list[QCheckBox] = []
        for idx, title in enumerate(TISSUE_TYPES):
            cb = QCheckBox(title)
            self.chk_tissues.append(cb)
            tissue_lay.addWidget(cb, idx // 2, idx % 2)
        left_col.addWidget(tissue_box)
        left_col.addStretch(1)

        top_row.addLayout(left_col)

        isolation_col = QVBoxLayout()
        isolation_col.setContentsMargins(0, 0, 0, 0)
        isolation_col.setSpacing(4)

        self.chk_isolation = QCheckBox("РР—Рћ-\nР›РЇР¦РРЇ")
        self.chk_isolation.setObjectName("isolationCheck")
        self.chk_isolation.toggled.connect(self._sync_isolation_bar)
        isolation_col.addWidget(self.chk_isolation, 0, Qt.AlignmentFlag.AlignHCenter)

        self.isolation_bar = QFrame()
        self.isolation_bar.setObjectName("form100Isolation")
        self.isolation_bar.setMinimumWidth(18)
        self.isolation_bar.setMaximumWidth(24)
        self.isolation_bar.setToolTip("РР—РћР›РЇР¦РРЇ")
        isolation_col.addWidget(self.isolation_bar, 1, Qt.AlignmentFlag.AlignHCenter)

        top_row.addLayout(isolation_col)

        self.editor = BodyMapWidget()
        top_row.addWidget(self.editor, 1)

        mp_box = QGroupBox("РњРµРґРёС†РёРЅСЃРєР°СЏ РїРѕРјРѕС‰СЊ")
        mp_box.setObjectName("form100Help")
        mp_lay = QFormLayout(mp_box)
        mp_lay.setContentsMargins(10, 8, 10, 8)
        mp_lay.setVerticalSpacing(5)

        self.mp_antibiotic = QCheckBox("РђРЅС‚РёР±РёРѕС‚РёРє")
        self.mp_antibiotic_dose = QLineEdit()
        self.mp_antibiotic_dose.setPlaceholderText("РґРѕР·Р°")
        self.mp_serum_pss = QCheckBox("РЎС‹РІРѕСЂРѕС‚РєР° РџРЎРЎ")
        self.mp_serum_pgs = QCheckBox("РЎС‹РІРѕСЂРѕС‚РєР° РџР“РЎ")
        self.mp_serum_dose = QLineEdit()
        self.mp_serum_dose.setPlaceholderText("РґРѕР·Р°")
        self.mp_toxoid = QLineEdit()
        self.mp_toxoid.setPlaceholderText("Р°РЅР°С‚РѕРєСЃРёРЅ (РєР°РєРѕР№)")
        self.mp_antidote = QLineEdit()
        self.mp_antidote.setPlaceholderText("Р°РЅС‚РёРґРѕС‚ (РєР°РєРѕР№)")
        self.mp_analgesic = QCheckBox("РћР±РµР·Р±РѕР»РёРІР°СЋС‰РµРµ")
        self.mp_analgesic_dose = QLineEdit()
        self.mp_analgesic_dose.setPlaceholderText("РґРѕР·Р°")
        self.mp_transfusion_blood = QCheckBox("РџРµСЂРµР»РёРІР°РЅРёРµ РєСЂРѕРІРё")
        self.mp_transfusion_substitute = QCheckBox("РљСЂРѕРІРµР·Р°РјРµРЅРёС‚РµР»Рё")
        self.mp_immobilization = QCheckBox("РРјРјРѕР±РёР»РёР·Р°С†РёСЏ")
        self.mp_bandage = QCheckBox("РџРµСЂРµРІСЏР·РєР°")

        mp_lay.addRow(self.mp_antibiotic, self.mp_antibiotic_dose)
        mp_lay.addRow(self.mp_serum_pss)
        mp_lay.addRow(self.mp_serum_pgs, self.mp_serum_dose)
        mp_lay.addRow("РђРЅР°С‚РѕРєСЃРёРЅ:", self.mp_toxoid)
        mp_lay.addRow("РђРЅС‚РёРґРѕС‚:", self.mp_antidote)
        mp_lay.addRow(self.mp_analgesic, self.mp_analgesic_dose)
        mp_lay.addRow(self.mp_transfusion_blood)
        mp_lay.addRow(self.mp_transfusion_substitute)
        mp_lay.addRow(self.mp_immobilization)
        mp_lay.addRow(self.mp_bandage)

        top_row.addWidget(mp_box)

        ident_box = QGroupBox("РРґРµРЅС‚РёС„РёРєР°С†РёСЏ вЂ” РѕСЃРЅРѕРІРЅРѕР№ Р±Р»Р°РЅРє")
        ident_box.setObjectName("form100Ident")
        ident_lay = QFormLayout(ident_box)
        ident_lay.setContentsMargins(10, 8, 10, 8)
        ident_lay.setVerticalSpacing(5)
        ident_lay.setHorizontalSpacing(12)

        self.main_issued_place = QLineEdit()
        self.main_issued_place.setPlaceholderText("РњРµРґ. РїСѓРЅРєС‚ / СѓС‡СЂРµР¶РґРµРЅРёРµ")

        issued_time_row = QHBoxLayout()
        self.main_issued_time = QTimeEdit()
        self.main_issued_time.setDisplayFormat("HH:mm")
        self.main_issued_date = QDateEdit()
        self.main_issued_date.setDisplayFormat("dd.MM.yyyy")
        self.main_issued_date.setCalendarPopup(True)
        issued_time_row.addWidget(self.main_issued_time)
        issued_time_row.addWidget(QLabel("РѕС‚"))
        issued_time_row.addWidget(self.main_issued_date)
        issued_time_row.addStretch(1)

        self.main_rank = QLineEdit()
        self.main_rank.setPlaceholderText("РІ/Р·РІР°РЅРёРµ")
        self.main_unit = QLineEdit()
        self.main_unit.setPlaceholderText("РІ/С‡Р°СЃС‚СЊ")
        self.main_full_name = QLineEdit()
        self.main_full_name.setPlaceholderText("С„Р°РјРёР»РёСЏ, РёРјСЏ, РѕС‚С‡РµСЃС‚РІРѕ")
        self.main_id_tag = QLineEdit()
        self.main_id_tag.setPlaceholderText("СѓРґРѕСЃС‚РѕРІРµСЂРµРЅРёРµ / Р¶РµС‚РѕРЅ в„–")

        injury_time_row = QHBoxLayout()
        self.main_injury_time = QTimeEdit()
        self.main_injury_time.setDisplayFormat("HH:mm")
        self.main_injury_date = QDateEdit()
        self.main_injury_date.setDisplayFormat("dd.MM.yyyy")
        self.main_injury_date.setCalendarPopup(True)
        injury_time_row.addWidget(self.main_injury_time)
        injury_time_row.addWidget(QLabel("РѕС‚"))
        injury_time_row.addWidget(self.main_injury_date)
        injury_time_row.addStretch(1)

        ident_lay.addRow("Р’С‹РґР°РЅР°:", self.main_issued_place)
        ident_lay.addRow("Р’СЂРµРјСЏ / РґР°С‚Р° РІС‹РґР°С‡Рё:", issued_time_row)
        ident_lay.addRow("Р’/Р·РІР°РЅРёРµ:", self.main_rank)
        ident_lay.addRow("Р’/С‡Р°СЃС‚СЊ:", self.main_unit)
        ident_lay.addRow("Р¤РРћ:", self.main_full_name)
        ident_lay.addRow("Р–РµС‚РѕРЅ в„–:", self.main_id_tag)
        ident_lay.addRow("Р Р°РЅРµРЅ / Р·Р°Р±РѕР»РµР»:", injury_time_row)

        root.addWidget(ident_box)

    def _sync_isolation_bar(self, checked: bool) -> None:
        self.isolation_bar.setProperty("active", bool(checked))
        self.isolation_bar.style().unpolish(self.isolation_bar)
        self.isolation_bar.style().polish(self.isolation_bar)
        self.isolation_bar.update()

    def set_values(self, payload: dict[str, str], markers: list[dict[str, Any]]) -> None:
        gender = str(payload.get("bodymap_gender") or "M")
        if gender in ("M", "F"):
            self.editor.set_gender(gender)
        self.editor.set_markers(markers)

        def _parse_json_list(raw: object) -> set[str]:
            try:
                parsed = json.loads(str(raw or "[]"))
                if isinstance(parsed, list):
                    return {str(x) for x in parsed}
            except (TypeError, ValueError, json.JSONDecodeError):
                return set()
            return set()

        lesion_vals = _parse_json_list(payload.get("lesion_json"))
        san_vals    = _parse_json_list(payload.get("san_loss_json"))
        tissue_vals = _parse_json_list(payload.get("bodymap_tissue_types_json"))

        for key, btn in self.lesion_widget.checks.items():
            active = key in lesion_vals or _truthy(payload.get(key))
            btn.setChecked(active)
            self.lesion_widget._sync_button_state(btn, active)
        for key, btn in self.san_loss_widget.checks.items():
            active = key in san_vals or _truthy(payload.get(key))
            btn.setChecked(active)
            self.san_loss_widget._sync_button_state(btn, active)
        for cb in self.chk_tissues:
            cb.setChecked(cb.text() in tissue_vals)

        isolation = _truthy(payload.get("isolation_required"))
        self.chk_isolation.setChecked(isolation)
        self._sync_isolation_bar(isolation)

        self.mp_antibiotic.setChecked(_truthy(payload.get("mp_antibiotic")))
        self.mp_antibiotic_dose.setText(str(payload.get("mp_antibiotic_dose") or ""))
        self.mp_serum_pss.setChecked(_truthy(payload.get("mp_serum_pss")))
        self.mp_serum_pgs.setChecked(_truthy(payload.get("mp_serum_pgs")))
        self.mp_serum_dose.setText(str(payload.get("mp_serum_dose") or ""))
        self.mp_toxoid.setText(str(payload.get("mp_toxoid") or ""))
        self.mp_antidote.setText(str(payload.get("mp_antidote") or ""))
        self.mp_analgesic.setChecked(_truthy(payload.get("mp_analgesic")))
        self.mp_analgesic_dose.setText(str(payload.get("mp_analgesic_dose") or ""))
        self.mp_transfusion_blood.setChecked(_truthy(payload.get("mp_transfusion_blood")))
        self.mp_transfusion_substitute.setChecked(_truthy(payload.get("mp_transfusion_substitute")))
        self.mp_immobilization.setChecked(_truthy(payload.get("mp_immobilization")))
        self.mp_bandage.setChecked(_truthy(payload.get("mp_bandage")))

        self.main_issued_place.setText(str(payload.get("main_issued_place") or ""))
        self.main_rank.setText(str(payload.get("main_rank") or ""))
        self.main_unit.setText(str(payload.get("main_unit") or ""))
        self.main_full_name.setText(str(payload.get("main_full_name") or ""))
        self.main_id_tag.setText(str(payload.get("main_id_tag") or ""))

        for time_edit, key in (
            (self.main_issued_time, "main_issued_time"),
            (self.main_injury_time, "main_injury_time"),
        ):
            val = str(payload.get(key) or "")
            t = QTime.fromString(val, "HH:mm")
            time_edit.setTime(t if t.isValid() else QTime(0, 0))

        for date_edit, key in (
            (self.main_issued_date, "main_issued_date"),
            (self.main_injury_date, "main_injury_date"),
        ):
            val = str(payload.get(key) or "")
            d = QDate.fromString(val, "dd.MM.yyyy")
            date_edit.setDate(d if d.isValid() else QDate.currentDate())

    def collect(self) -> tuple[dict[str, str], list[dict[str, Any]]]:
        payload: dict[str, str] = {}

        payload["bodymap_gender"] = self.editor.gender()

        lesion_sel = [k for k, b in self.lesion_widget.checks.items() if b.isChecked()]
        san_sel    = [k for k, b in self.san_loss_widget.checks.items() if b.isChecked()]
        tissue_sel = [cb.text() for cb in self.chk_tissues if cb.isChecked()]

        payload["lesion_json"]               = json.dumps(lesion_sel, ensure_ascii=False)
        payload["san_loss_json"]             = json.dumps(san_sel, ensure_ascii=False)
        payload["bodymap_tissue_types_json"] = json.dumps(tissue_sel, ensure_ascii=False)

        for key, btn in self.lesion_widget.checks.items():
            payload[key] = "1" if btn.isChecked() else "0"
        for key, btn in self.san_loss_widget.checks.items():
            payload[key] = "1" if btn.isChecked() else "0"
        payload["isolation_required"] = "1" if self.chk_isolation.isChecked() else "0"

        payload["mp_antibiotic"]             = "1" if self.mp_antibiotic.isChecked() else "0"
        payload["mp_antibiotic_dose"]        = self.mp_antibiotic_dose.text().strip()
        payload["mp_serum_pss"]              = "1" if self.mp_serum_pss.isChecked() else "0"
        payload["mp_serum_pgs"]              = "1" if self.mp_serum_pgs.isChecked() else "0"
        payload["mp_serum_dose"]             = self.mp_serum_dose.text().strip()
        payload["mp_toxoid"]                 = self.mp_toxoid.text().strip()
        payload["mp_antidote"]               = self.mp_antidote.text().strip()
        payload["mp_analgesic"]              = "1" if self.mp_analgesic.isChecked() else "0"
        payload["mp_analgesic_dose"]         = self.mp_analgesic_dose.text().strip()
        payload["mp_transfusion_blood"]      = "1" if self.mp_transfusion_blood.isChecked() else "0"
        payload["mp_transfusion_substitute"] = "1" if self.mp_transfusion_substitute.isChecked() else "0"
        payload["mp_immobilization"]         = "1" if self.mp_immobilization.isChecked() else "0"
        payload["mp_bandage"]                = "1" if self.mp_bandage.isChecked() else "0"

        payload["main_issued_place"] = self.main_issued_place.text().strip()
        payload["main_rank"]         = self.main_rank.text().strip()
        payload["main_unit"]         = self.main_unit.text().strip()
        payload["main_full_name"]    = self.main_full_name.text().strip()
        payload["main_id_tag"]       = self.main_id_tag.text().strip()
        payload["main_issued_time"]  = self.main_issued_time.time().toString("HH:mm")
        payload["main_issued_date"]  = self.main_issued_date.date().toString("dd.MM.yyyy")
        payload["main_injury_time"]  = self.main_injury_time.time().toString("HH:mm")
        payload["main_injury_date"]  = self.main_injury_date.date().toString("dd.MM.yyyy")

        markers = self.editor.markers()
        payload["bodymap_annotations_json"] = json.dumps(markers, ensure_ascii=False)

        return payload, markers

    def set_locked(self, locked: bool) -> None:
        self.editor.set_markers_enabled(not locked)
        enabled = not locked

        self.lesion_widget.set_enabled(enabled)
        self.san_loss_widget.set_enabled(enabled)
        for cb in self.chk_tissues:
            cb.setEnabled(enabled)
        self.chk_isolation.setEnabled(enabled)

        for mp_w in (
            self.mp_antibiotic, self.mp_antibiotic_dose,
            self.mp_serum_pss, self.mp_serum_pgs, self.mp_serum_dose,
            self.mp_toxoid, self.mp_antidote,
            self.mp_analgesic, self.mp_analgesic_dose,
            self.mp_transfusion_blood, self.mp_transfusion_substitute,
            self.mp_immobilization, self.mp_bandage,
        ):
            mp_w.setEnabled(enabled)

        for id_w in (
            self.main_issued_place, self.main_issued_time, self.main_issued_date,
            self.main_rank, self.main_unit, self.main_full_name, self.main_id_tag,
            self.main_injury_time, self.main_injury_date,
        ):
            id_w.setEnabled(enabled)

