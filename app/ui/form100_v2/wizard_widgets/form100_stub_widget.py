from __future__ import annotations

import json
from datetime import datetime

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDateEdit,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QRadioButton,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.form100_v2.wizard_widgets.icon_select_widget import IconSelectWidget

STUB_MED_HELP_ITEMS: tuple[tuple[str, str], ...] = (
    ("stub_med_help_antibiotic", "Антибиотик"),
    ("stub_med_help_serum", "Сыворотка ПСС/ПГС"),
    ("stub_med_help_toxoid", "Анатоксин"),
    ("stub_med_help_antidote", "Антидот"),
    ("stub_med_help_analgesic", "Обезболивающее"),
    ("stub_med_help_transfusion", "Переливание"),
    ("stub_med_help_immobilization", "Иммобилизация/перевязка"),
    ("stub_med_help_tourniquet", "Жгут/санобработка"),
)


def _is_truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_date(raw: str) -> QDate:
    text = raw.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text, fmt)  # noqa: DTZ007
            return QDate(dt.year, dt.month, dt.day)
        except ValueError:
            continue
    return QDate.currentDate()


def _parse_time(raw: str) -> QTime:
    text = raw.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            dt = datetime.strptime(text, fmt)  # noqa: DTZ007
            return QTime(dt.hour, dt.minute, dt.second)
        except ValueError:
            continue
    return QTime.currentTime()


class Form100StubWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        top = QGroupBox("Корешок")
        top.setObjectName("form100StubSection")
        top_form = QFormLayout(top)
        top_form.setContentsMargins(10, 8, 10, 8)
        top_form.setVerticalSpacing(6)
        self.stub_issued_time = QTimeEdit()
        self.stub_issued_time.setDisplayFormat("HH:mm")
        self.stub_issued_date = QDateEdit()
        self.stub_issued_date.setDisplayFormat("dd.MM.yyyy")
        self.stub_issued_date.setCalendarPopup(True)
        self.stub_rank = QLineEdit()
        self.stub_unit = QLineEdit()
        self.stub_full_name = QLineEdit()
        self.stub_id_tag = QLineEdit()
        self.stub_injury_time = QTimeEdit()
        self.stub_injury_time.setDisplayFormat("HH:mm")
        self.stub_injury_date = QDateEdit()
        self.stub_injury_date.setDisplayFormat("dd.MM.yyyy")
        self.stub_injury_date.setCalendarPopup(True)
        top_form.addRow("Выдана (время)", self.stub_issued_time)
        top_form.addRow("Выдана (дата)", self.stub_issued_date)
        top_form.addRow("В/звание", self.stub_rank)
        top_form.addRow("В/часть", self.stub_unit)
        top_form.addRow("ФИО", self.stub_full_name)
        top_form.addRow("Жетон / удостоверение", self.stub_id_tag)
        top_form.addRow("Ранен (время)", self.stub_injury_time)
        top_form.addRow("Ранен (дата)", self.stub_injury_date)
        root.addWidget(top)

        evac = QGroupBox("Эвакуация (корешок)")
        evac.setObjectName("form100StubSection")
        evac_layout = QVBoxLayout(evac)
        evac_layout.setContentsMargins(10, 8, 10, 8)
        evac_layout.setSpacing(8)
        self.stub_evacuation_method = QButtonGroup(self)
        method_row = QHBoxLayout()
        method_row.setContentsMargins(0, 0, 0, 0)
        self.rb_airplane = QRadioButton("Самолёт")
        self.rb_ambu = QRadioButton("Санг.")
        self.rb_truck = QRadioButton("Грузавто")
        self.stub_evacuation_method.addButton(self.rb_airplane)
        self.stub_evacuation_method.addButton(self.rb_ambu)
        self.stub_evacuation_method.addButton(self.rb_truck)
        method_row.addWidget(self.rb_airplane)
        method_row.addWidget(self.rb_ambu)
        method_row.addWidget(self.rb_truck)
        method_row.addStretch(1)
        evac_layout.addLayout(method_row)

        self.stub_evacuation_dest = IconSelectWidget(
            (
                ("lying", "Лёжа"),
                ("sitting", "Сидя"),
                ("stretcher", "Носилки"),
            )
        )
        evac_layout.addWidget(self.stub_evacuation_dest)
        root.addWidget(evac)

        help_grp = QGroupBox("Медицинская помощь (корешок)")
        help_grp.setObjectName("form100StubSection")
        help_layout = QVBoxLayout(help_grp)
        help_layout.setContentsMargins(10, 8, 10, 8)
        help_layout.setSpacing(6)
        self.stub_med_help_checks: dict[str, QCheckBox] = {}
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        for idx, (key, title) in enumerate(STUB_MED_HELP_ITEMS):
            cb = QCheckBox(title)
            self.stub_med_help_checks[key] = cb
            grid.addWidget(cb, idx // 2, idx % 2)
        help_layout.addLayout(grid)
        self.stub_antibiotic_dose = QLineEdit()
        self.stub_pss_pgs_dose = QLineEdit()
        self.stub_toxoid_type = QLineEdit()
        self.stub_antidote_type = QLineEdit()
        self.stub_analgesic_dose = QLineEdit()
        help_form = QFormLayout()
        help_form.addRow("Доза антибиотика", self.stub_antibiotic_dose)
        help_form.addRow("Доза ПСС/ПГС", self.stub_pss_pgs_dose)
        help_form.addRow("Анатоксин", self.stub_toxoid_type)
        help_form.addRow("Антидот", self.stub_antidote_type)
        help_form.addRow("Обезболивающее", self.stub_analgesic_dose)
        help_layout.addLayout(help_form)

        self.stub_transfusion = QCheckBox("Переливание")
        self.stub_immobilization = QCheckBox("Иммобилизация / перевязка")
        self.stub_tourniquet = QCheckBox("Жгут / санобработка")
        help_layout.addWidget(self.stub_transfusion)
        help_layout.addWidget(self.stub_immobilization)
        help_layout.addWidget(self.stub_tourniquet)
        root.addWidget(help_grp)

        diag = QGroupBox("Диагноз (корешок)")
        diag.setObjectName("form100StubSection")
        diag_layout = QVBoxLayout(diag)
        diag_layout.setContentsMargins(10, 8, 10, 8)
        self.stub_diagnosis = QTextEdit()
        self.stub_diagnosis.setFixedHeight(58)
        diag_layout.addWidget(self.stub_diagnosis)
        root.addWidget(diag)
        root.addStretch(1)

    def _set_evacuation_method(self, value: str) -> None:
        if value == "airplane":
            self.rb_airplane.setChecked(True)
        elif value == "ambu":
            self.rb_ambu.setChecked(True)
        elif value == "truck":
            self.rb_truck.setChecked(True)
        else:
            self.stub_evacuation_method.setExclusive(False)
            self.rb_airplane.setChecked(False)
            self.rb_ambu.setChecked(False)
            self.rb_truck.setChecked(False)
            self.stub_evacuation_method.setExclusive(True)

    def _evacuation_method(self) -> str:
        if self.rb_airplane.isChecked():
            return "airplane"
        if self.rb_ambu.isChecked():
            return "ambu"
        if self.rb_truck.isChecked():
            return "truck"
        return ""

    def set_values(self, payload: dict[str, str]) -> None:
        self.stub_issued_time.setTime(_parse_time(str(payload.get("stub_issued_time") or "")))
        self.stub_issued_date.setDate(_parse_date(str(payload.get("stub_issued_date") or "")))
        self.stub_rank.setText(str(payload.get("stub_rank") or ""))
        self.stub_unit.setText(str(payload.get("stub_unit") or ""))
        self.stub_full_name.setText(str(payload.get("stub_full_name") or ""))
        self.stub_id_tag.setText(str(payload.get("stub_id_tag") or ""))
        self.stub_injury_time.setTime(_parse_time(str(payload.get("stub_injury_time") or "")))
        self.stub_injury_date.setDate(_parse_date(str(payload.get("stub_injury_date") or "")))
        self._set_evacuation_method(str(payload.get("stub_evacuation_method") or ""))
        self.stub_evacuation_dest.set_value(str(payload.get("stub_evacuation_dest") or ""))

        selected: set[str] = set()
        try:
            raw = json.loads(str(payload.get("stub_med_help_json") or "[]"))
            if isinstance(raw, list):
                selected = {str(x) for x in raw}
        except Exception:  # noqa: BLE001
            selected = set()
        for key, cb in self.stub_med_help_checks.items():
            cb.setChecked(key in selected or _is_truthy(payload.get(key)))

        self.stub_antibiotic_dose.setText(str(payload.get("stub_antibiotic_dose") or ""))
        self.stub_pss_pgs_dose.setText(str(payload.get("stub_pss_pgs_dose") or ""))
        self.stub_toxoid_type.setText(str(payload.get("stub_toxoid_type") or ""))
        self.stub_antidote_type.setText(str(payload.get("stub_antidote_type") or ""))
        self.stub_analgesic_dose.setText(str(payload.get("stub_analgesic_dose") or ""))
        self.stub_transfusion.setChecked(_is_truthy(payload.get("stub_transfusion")))
        self.stub_immobilization.setChecked(_is_truthy(payload.get("stub_immobilization")))
        self.stub_tourniquet.setChecked(_is_truthy(payload.get("stub_tourniquet")))
        self.stub_diagnosis.setPlainText(str(payload.get("stub_diagnosis") or ""))

    def collect(self) -> dict[str, str]:
        selected = [key for key, cb in self.stub_med_help_checks.items() if cb.isChecked()]
        out: dict[str, str] = {
            "stub_issued_time": self.stub_issued_time.time().toString("HH:mm"),
            "stub_issued_date": self.stub_issued_date.date().toString("dd.MM.yyyy"),
            "stub_rank": self.stub_rank.text().strip(),
            "stub_unit": self.stub_unit.text().strip(),
            "stub_full_name": self.stub_full_name.text().strip(),
            "stub_id_tag": self.stub_id_tag.text().strip(),
            "stub_injury_time": self.stub_injury_time.time().toString("HH:mm"),
            "stub_injury_date": self.stub_injury_date.date().toString("dd.MM.yyyy"),
            "stub_evacuation_method": self._evacuation_method(),
            "stub_evacuation_dest": self.stub_evacuation_dest.value(),
            "stub_med_help_json": json.dumps(selected, ensure_ascii=False),
            "stub_antibiotic_dose": self.stub_antibiotic_dose.text().strip(),
            "stub_pss_pgs_dose": self.stub_pss_pgs_dose.text().strip(),
            "stub_toxoid_type": self.stub_toxoid_type.text().strip(),
            "stub_antidote_type": self.stub_antidote_type.text().strip(),
            "stub_analgesic_dose": self.stub_analgesic_dose.text().strip(),
            "stub_transfusion": "1" if self.stub_transfusion.isChecked() else "0",
            "stub_immobilization": "1" if self.stub_immobilization.isChecked() else "0",
            "stub_tourniquet": "1" if self.stub_tourniquet.isChecked() else "0",
            "stub_diagnosis": self.stub_diagnosis.toPlainText().strip(),
        }
        for key, cb in self.stub_med_help_checks.items():
            out[key] = "1" if cb.isChecked() else "0"
        return out

    def set_enabled(self, enabled: bool) -> None:
        self.setEnabled(enabled)
