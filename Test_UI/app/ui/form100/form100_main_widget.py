"""Form100MainWidget — центральная часть бланка Формы 100.

Компоновка (слева направо):
  [Вид поражения | Изоляция] | BodyMapWidget (4 силуэта) | [Мед. помощь]

Ниже — QGroupBox «Идентификация» (поля основного бланка: ФИО, жетон, дата).
"""
from __future__ import annotations

import json

from PySide6.QtCore import Qt
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
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QDate, QTime

from .bodymap_widget import BodyMapWidget
from .lesion_type_widget import LesionTypeWidget

# ── Константы для типов поражений ────────────────────────────────────────────

LESION_ITEMS: tuple[tuple[str, str], ...] = (
    ("lesion_gunshot",    "О  Огнестрельное"),
    ("lesion_nuclear",    "Я  Ядерное"),
    ("lesion_chemical",   "Х  Химическое"),
    ("lesion_biological", "Бак. Бактериол."),
    ("lesion_other",      "Другие"),
    ("lesion_frostbite",  "Отм. Отморожение"),
    ("lesion_burn",       "Б  Ожог"),
    ("lesion_misc",       "И  Иное"),
)

SAN_LOSS_ITEMS: tuple[tuple[str, str], ...] = (
    ("san_loss_gunshot",    "О  Огнестрельное"),
    ("san_loss_nuclear",    "Я  Ядерное"),
    ("san_loss_chemical",   "Х  Химическое"),
    ("san_loss_biological", "Бак. Бактериол."),
    ("san_loss_other",      "Другие"),
    ("san_loss_frostbite",  "Отм. Отморожение"),
    ("san_loss_burn",       "Б  Ожог"),
    ("san_loss_misc",       "И  Иное"),
)

TISSUE_TYPES: tuple[str, ...] = (
    "мягкие ткани",
    "кости",
    "сосуды",
    "полостные раны",
    "ожоги",
)


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Form100MainWidget(QWidget):
    """Основной бланк Формы 100: поражения + схема тела + медицинская помощь + идентификация."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # ── Верхний ряд: [Поражения + Изоляция | BodyMap | Мед. помощь] ────
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        root.addLayout(top_row, 1)

        # ── Левый столбец: виды поражений + изоляция ─────────────────────
        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(6)

        lesion_box = QGroupBox("Вид поражения")
        lesion_box.setObjectName("form100Lesion")
        lesion_lay = QVBoxLayout(lesion_box)
        lesion_lay.setContentsMargins(8, 6, 8, 6)
        self.lesion_widget = LesionTypeWidget(LESION_ITEMS)
        lesion_lay.addWidget(self.lesion_widget)
        left_col.addWidget(lesion_box)

        san_box = QGroupBox("Вид сан. потерь")
        san_box.setObjectName("form100Lesion")
        san_lay = QVBoxLayout(san_box)
        san_lay.setContentsMargins(8, 6, 8, 6)
        self.san_loss_widget = LesionTypeWidget(SAN_LOSS_ITEMS)
        san_lay.addWidget(self.san_loss_widget)
        left_col.addWidget(san_box)

        tissue_box = QGroupBox("Типы тканей")
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

        # ── Полоса «ИЗОЛЯЦИЯ» (вертикальная, 22 px) ──────────────────────
        isolation_col = QVBoxLayout()
        isolation_col.setContentsMargins(0, 0, 0, 0)
        isolation_col.setSpacing(4)

        self.chk_isolation = QCheckBox("ИЗО-\nЛЯЦИЯ")
        self.chk_isolation.setObjectName("isolationCheck")
        self.chk_isolation.toggled.connect(self._sync_isolation_bar)
        isolation_col.addWidget(self.chk_isolation, 0, Qt.AlignmentFlag.AlignHCenter)

        self.isolation_bar = QFrame()
        self.isolation_bar.setObjectName("form100Isolation")
        self.isolation_bar.setFixedWidth(22)
        self.isolation_bar.setToolTip("ИЗОЛЯЦИЯ")
        isolation_col.addWidget(self.isolation_bar, 1, Qt.AlignmentFlag.AlignHCenter)

        top_row.addLayout(isolation_col)

        # ── Центр: BodyMapWidget ──────────────────────────────────────────
        self.editor = BodyMapWidget()
        top_row.addWidget(self.editor, 1)

        # ── Правый столбец: Медицинская помощь ───────────────────────────
        mp_box = QGroupBox("Медицинская помощь")
        mp_box.setObjectName("form100Help")
        mp_lay = QFormLayout(mp_box)
        mp_lay.setContentsMargins(10, 8, 10, 8)
        mp_lay.setVerticalSpacing(5)

        self.mp_antibiotic = QCheckBox("Антибиотик")
        self.mp_antibiotic_dose = QLineEdit()
        self.mp_antibiotic_dose.setPlaceholderText("доза")
        self.mp_serum_pss = QCheckBox("Сыворотка ПСС")
        self.mp_serum_pgs = QCheckBox("Сыворотка ПГС")
        self.mp_serum_dose = QLineEdit()
        self.mp_serum_dose.setPlaceholderText("доза")
        self.mp_toxoid = QLineEdit()
        self.mp_toxoid.setPlaceholderText("анатоксин (какой)")
        self.mp_antidote = QLineEdit()
        self.mp_antidote.setPlaceholderText("антидот (какой)")
        self.mp_analgesic = QCheckBox("Обезболивающее")
        self.mp_analgesic_dose = QLineEdit()
        self.mp_analgesic_dose.setPlaceholderText("доза")
        self.mp_transfusion_blood = QCheckBox("Переливание крови")
        self.mp_transfusion_substitute = QCheckBox("Кровезаменители")
        self.mp_immobilization = QCheckBox("Иммобилизация")
        self.mp_bandage = QCheckBox("Перевязка")

        mp_lay.addRow(self.mp_antibiotic, self.mp_antibiotic_dose)
        mp_lay.addRow(self.mp_serum_pss)
        mp_lay.addRow(self.mp_serum_pgs, self.mp_serum_dose)
        mp_lay.addRow("Анатоксин:", self.mp_toxoid)
        mp_lay.addRow("Антидот:", self.mp_antidote)
        mp_lay.addRow(self.mp_analgesic, self.mp_analgesic_dose)
        mp_lay.addRow(self.mp_transfusion_blood)
        mp_lay.addRow(self.mp_transfusion_substitute)
        mp_lay.addRow(self.mp_immobilization)
        mp_lay.addRow(self.mp_bandage)

        top_row.addWidget(mp_box)

        # ── Нижний блок: Идентификация (основной бланк) ──────────────────
        ident_box = QGroupBox("Идентификация — основной бланк")
        ident_box.setObjectName("form100Ident")
        ident_lay = QFormLayout(ident_box)
        ident_lay.setContentsMargins(10, 8, 10, 8)
        ident_lay.setVerticalSpacing(5)
        ident_lay.setHorizontalSpacing(12)

        self.main_issued_place = QLineEdit()
        self.main_issued_place.setPlaceholderText("Мед. пункт / учреждение")

        issued_time_row = QHBoxLayout()
        self.main_issued_time = QTimeEdit()
        self.main_issued_time.setDisplayFormat("HH:mm")
        self.main_issued_date = QDateEdit()
        self.main_issued_date.setDisplayFormat("dd.MM.yyyy")
        self.main_issued_date.setCalendarPopup(True)
        issued_time_row.addWidget(self.main_issued_time)
        issued_time_row.addWidget(QLabel("от"))
        issued_time_row.addWidget(self.main_issued_date)
        issued_time_row.addStretch(1)

        self.main_rank = QLineEdit()
        self.main_rank.setPlaceholderText("в/звание")
        self.main_unit = QLineEdit()
        self.main_unit.setPlaceholderText("в/часть")
        self.main_full_name = QLineEdit()
        self.main_full_name.setPlaceholderText("фамилия, имя, отчество")
        self.main_id_tag = QLineEdit()
        self.main_id_tag.setPlaceholderText("удостоверение / жетон №")

        injury_time_row = QHBoxLayout()
        self.main_injury_time = QTimeEdit()
        self.main_injury_time.setDisplayFormat("HH:mm")
        self.main_injury_date = QDateEdit()
        self.main_injury_date.setDisplayFormat("dd.MM.yyyy")
        self.main_injury_date.setCalendarPopup(True)
        injury_time_row.addWidget(self.main_injury_time)
        injury_time_row.addWidget(QLabel("от"))
        injury_time_row.addWidget(self.main_injury_date)
        injury_time_row.addStretch(1)

        ident_lay.addRow("Выдана:", self.main_issued_place)
        ident_lay.addRow("Время / дата выдачи:", issued_time_row)
        ident_lay.addRow("В/звание:", self.main_rank)
        ident_lay.addRow("В/часть:", self.main_unit)
        ident_lay.addRow("ФИО:", self.main_full_name)
        ident_lay.addRow("Жетон №:", self.main_id_tag)
        ident_lay.addRow("Ранен / заболел:", injury_time_row)

        root.addWidget(ident_box)

    # ── Вспомогательные ──────────────────────────────────────────────────────

    def _sync_isolation_bar(self, checked: bool) -> None:
        self.isolation_bar.setProperty("active", bool(checked))
        self.isolation_bar.style().unpolish(self.isolation_bar)
        self.isolation_bar.style().polish(self.isolation_bar)
        self.isolation_bar.update()

    # ── Публичный API ─────────────────────────────────────────────────────────

    def set_values(self, payload: dict[str, str], markers: list[dict]) -> None:
        # Bodymap
        gender = str(payload.get("bodymap_gender") or "M")
        if gender in ("M", "F"):
            self.editor.set_gender(gender)
        self.editor.set_markers(markers)

        # Виды поражений
        def _parse_json_list(raw: object) -> set[str]:
            try:
                parsed = json.loads(str(raw or "[]"))
                if isinstance(parsed, list):
                    return {str(x) for x in parsed}
            except Exception:
                pass
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

        # Медицинская помощь
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

        # Идентификация (основной бланк)
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

    def collect(self) -> tuple[dict[str, str], list[dict]]:
        payload: dict[str, str] = {}

        # Bodymap
        payload["bodymap_gender"] = self.editor.gender()

        # Виды поражений
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

        # Медицинская помощь
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

        # Идентификация
        payload["main_issued_place"] = self.main_issued_place.text().strip()
        payload["main_rank"]         = self.main_rank.text().strip()
        payload["main_unit"]         = self.main_unit.text().strip()
        payload["main_full_name"]    = self.main_full_name.text().strip()
        payload["main_id_tag"]       = self.main_id_tag.text().strip()
        payload["main_issued_time"]  = self.main_issued_time.time().toString("HH:mm")
        payload["main_issued_date"]  = self.main_issued_date.date().toString("dd.MM.yyyy")
        payload["main_injury_time"]  = self.main_injury_time.time().toString("HH:mm")
        payload["main_injury_date"]  = self.main_injury_date.date().toString("dd.MM.yyyy")

        # Аннотации bodymap
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
