from __future__ import annotations

from datetime import date
from typing import Any

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.form100_v2_dto import (
    Form100CardV2Dto,
    Form100CreateV2Request,
    Form100DataV2Dto,
    Form100SignV2Request,
    Form100UpdateV2Request,
)
from app.ui.form100.widgets.validation_banner import ValidationBanner
from app.ui.form100_v2.widgets.bodymap_editor_v2 import BodymapEditorV2

_LESION_KEYS = (
    ("lesion_gunshot", "Огнестрельное"),
    ("lesion_nuclear", "Ядерное"),
    ("lesion_chemical", "Химическое"),
    ("lesion_biological", "Бактериологическое"),
    ("lesion_other", "Другие"),
    ("lesion_frostbite", "Отморожение"),
    ("lesion_burn", "Ожог"),
    ("lesion_misc", "Иное"),
)

_SAN_LOSS_KEYS = (
    ("san_loss_gunshot", "Огнестрельное"),
    ("san_loss_nuclear", "Ядерное"),
    ("san_loss_chemical", "Химическое"),
    ("san_loss_biological", "Бактериологическое"),
    ("san_loss_other", "Другие"),
    ("san_loss_frostbite", "Отморожение"),
    ("san_loss_burn", "Ожог"),
    ("san_loss_misc", "Иное"),
)

_TISSUE_TYPES = ("мягкие ткани", "кости", "сосуды", "полостные раны", "ожоги")
_STUB_MED_HELP_OPTIONS = (
    "Введено: антибиотик",
    "Сыворотка ПСС/ПГС",
    "Анатоксин",
    "Антидот",
    "Обезболивающее средство",
    "Произведено: переливание крови, кровезаменителей",
    "Иммобилизация, перевязка",
    "Наложен жгут, санобработка",
)


class Form100EditorV2(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_card: Form100CardV2Dto | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.validation_banner = ValidationBanner()
        root.addWidget(self.validation_banner)

        root.addWidget(self._build_stub_block())
        root.addWidget(self._build_main_block())
        root.addWidget(self._build_bodymap_block())
        root.addWidget(self._build_medical_help_block())
        root.addWidget(self._build_bottom_block())
        root.addWidget(self._build_flags_block())
        root.addStretch()

    def _build_stub_block(self) -> QWidget:
        box = QGroupBox("Корешок")
        form = QFormLayout(box)

        self.stub_issued_date = QDateEdit()
        self.stub_issued_date.setDisplayFormat("dd.MM.yyyy")
        self.stub_issued_date.setCalendarPopup(True)
        self.stub_issued_date.setDate(QDate.currentDate())
        self.stub_issued_time = QTimeEdit()
        self.stub_issued_time.setDisplayFormat("HH:mm")
        self.stub_issued_time.setTime(QTime.currentTime())

        self.stub_rank = QLineEdit()
        self.stub_unit = QLineEdit()
        self.stub_full_name = QLineEdit()
        self.stub_id_tag = QLineEdit()

        self.stub_injury_date = QDateEdit()
        self.stub_injury_date.setDisplayFormat("dd.MM.yyyy")
        self.stub_injury_date.setCalendarPopup(True)
        self.stub_injury_date.setDate(QDate.currentDate())
        self.stub_injury_time = QTimeEdit()
        self.stub_injury_time.setDisplayFormat("HH:mm")
        self.stub_injury_time.setTime(QTime.currentTime())

        self.stub_evac_method = QComboBox()
        self.stub_evac_method.addItem("Самолётом", "airplane")
        self.stub_evac_method.addItem("Санг.", "ambu")
        self.stub_evac_method.addItem("Грузавто", "truck")

        self.stub_evac_dest = QComboBox()
        self.stub_evac_dest.addItem("Лёжа", "lying")
        self.stub_evac_dest.addItem("Сидя", "sitting")
        self.stub_evac_dest.addItem("Носилки", "stretcher")

        self.stub_med_help_checks: dict[str, QCheckBox] = {}
        med_help_widget = QWidget()
        med_help_layout = QVBoxLayout(med_help_widget)
        med_help_layout.setContentsMargins(0, 0, 0, 0)
        med_help_layout.setSpacing(4)
        for item in _STUB_MED_HELP_OPTIONS:
            check = QCheckBox(item)
            self.stub_med_help_checks[item] = check
            med_help_layout.addWidget(check)

        self.stub_antibiotic_dose = QLineEdit()
        self.stub_pss_pgs_dose = QLineEdit()
        self.stub_toxoid_type = QLineEdit()
        self.stub_antidote_type = QLineEdit()
        self.stub_analgesic_dose = QLineEdit()
        self.stub_transfusion = QCheckBox("Переливание крови/кровезаменителей")
        self.stub_immobilization = QCheckBox("Иммобилизация, перевязка")
        self.stub_tourniquet = QCheckBox("Жгут / санобработка")
        self.stub_diagnosis = QTextEdit()
        self.stub_diagnosis.setFixedHeight(56)

        form.addRow("Выдана — дата", self.stub_issued_date)
        form.addRow("Выдана — время", self.stub_issued_time)
        form.addRow("В/звание", self.stub_rank)
        form.addRow("В/часть", self.stub_unit)
        form.addRow("ФИО", self.stub_full_name)
        form.addRow("Жетон/ID", self.stub_id_tag)
        form.addRow("Дата ранения", self.stub_injury_date)
        form.addRow("Время ранения", self.stub_injury_time)
        form.addRow("Эвакуация", self.stub_evac_method)
        form.addRow("Положение", self.stub_evac_dest)
        form.addRow("Мед. помощь (подчеркнуть)", med_help_widget)
        form.addRow("Доза антибиотика", self.stub_antibiotic_dose)
        form.addRow("Сыворотка ПСС/ПГС", self.stub_pss_pgs_dose)
        form.addRow("Анатоксин", self.stub_toxoid_type)
        form.addRow("Антидот", self.stub_antidote_type)
        form.addRow("Обезболивание", self.stub_analgesic_dose)
        form.addRow(self.stub_transfusion)
        form.addRow(self.stub_immobilization)
        form.addRow(self.stub_tourniquet)
        form.addRow("Диагноз", self.stub_diagnosis)
        return box

    def _build_main_block(self) -> QWidget:
        box = QGroupBox("Основной бланк: идентификация и поражения")
        layout = QVBoxLayout(box)
        form = QFormLayout()
        self.main_full_name = QLineEdit()
        self.main_unit = QLineEdit()
        self.main_id_tag = QLineEdit()
        self.birth_date = QDateEdit()
        self.birth_date.setDisplayFormat("dd.MM.yyyy")
        self.birth_date.setCalendarPopup(True)
        self.birth_date.setDate(QDate.currentDate())
        self.main_rank = QLineEdit()
        self.main_issued_place = QLineEdit()
        self.main_issued_date = QDateEdit()
        self.main_issued_date.setDisplayFormat("dd.MM.yyyy")
        self.main_issued_date.setCalendarPopup(True)
        self.main_issued_date.setDate(QDate.currentDate())
        self.main_issued_time = QTimeEdit()
        self.main_issued_time.setDisplayFormat("HH:mm")
        self.main_issued_time.setTime(QTime.currentTime())
        self.main_injury_date = QDateEdit()
        self.main_injury_date.setDisplayFormat("dd.MM.yyyy")
        self.main_injury_date.setCalendarPopup(True)
        self.main_injury_date.setDate(QDate.currentDate())
        self.main_injury_time = QTimeEdit()
        self.main_injury_time.setDisplayFormat("HH:mm")
        self.main_injury_time.setTime(QTime.currentTime())

        form.addRow("ФИО", self.main_full_name)
        form.addRow("Подразделение", self.main_unit)
        form.addRow("Жетон/ID", self.main_id_tag)
        form.addRow("Дата рождения", self.birth_date)
        form.addRow("В/звание", self.main_rank)
        form.addRow("Мед. пункт (выдана)", self.main_issued_place)
        form.addRow("Выдана — дата", self.main_issued_date)
        form.addRow("Выдана — время", self.main_issued_time)
        form.addRow("Дата ранения", self.main_injury_date)
        form.addRow("Время ранения", self.main_injury_time)
        layout.addLayout(form)

        checklist_row = QHBoxLayout()
        lesion_box = QGroupBox("Вид поражения")
        lesion_layout = QVBoxLayout(lesion_box)
        self.lesion_checks: dict[str, QCheckBox] = {}
        for key, label in _LESION_KEYS:
            check = QCheckBox(label)
            self.lesion_checks[key] = check
            lesion_layout.addWidget(check)
        checklist_row.addWidget(lesion_box)

        san_loss_box = QGroupBox("Вид санитарных потерь")
        san_loss_layout = QVBoxLayout(san_loss_box)
        self.san_loss_checks: dict[str, QCheckBox] = {}
        for key, label in _SAN_LOSS_KEYS:
            check = QCheckBox(label)
            self.san_loss_checks[key] = check
            san_loss_layout.addWidget(check)
        checklist_row.addWidget(san_loss_box)

        self.isolation_required = QCheckBox("Изоляция требуется")
        isolation_box = QGroupBox("Изоляция")
        isolation_layout = QVBoxLayout(isolation_box)
        isolation_layout.addWidget(self.isolation_required)
        isolation_layout.addStretch()
        checklist_row.addWidget(isolation_box)
        layout.addLayout(checklist_row)
        return box
    def _build_bodymap_block(self) -> QWidget:
        box = QGroupBox("Схема тела")
        layout = QVBoxLayout(box)
        tissue_row = QHBoxLayout()
        tissue_row.addWidget(QLabel("Отмеченные типы ткани:"))
        self.tissue_checks: dict[str, QCheckBox] = {}
        for item in _TISSUE_TYPES:
            check = QCheckBox(item)
            self.tissue_checks[item] = check
            tissue_row.addWidget(check)
        tissue_row.addStretch()
        layout.addLayout(tissue_row)
        self.bodymap_editor = BodymapEditorV2()
        layout.addWidget(self.bodymap_editor)
        return box

    def _build_medical_help_block(self) -> QWidget:
        box = QGroupBox("Медицинская помощь")
        form = QFormLayout(box)
        self.mp_antibiotic = QCheckBox("Антибиотик")
        self.mp_antibiotic_dose = QLineEdit()
        self.mp_serum_pss = QCheckBox("Сыворотка ПСС")
        self.mp_serum_pgs = QCheckBox("Сыворотка ПГС")
        self.mp_serum_dose = QLineEdit()
        self.mp_toxoid = QLineEdit()
        self.mp_antidote = QLineEdit()
        self.mp_analgesic = QCheckBox("Обезболивание")
        self.mp_analgesic_dose = QLineEdit()
        self.mp_transfusion_blood = QCheckBox("Переливание крови")
        self.mp_transfusion_substitute = QCheckBox("Переливание кровезаменителей")
        self.mp_immobilization = QCheckBox("Иммобилизация")
        self.mp_bandage = QCheckBox("Перевязка")

        form.addRow(self.mp_antibiotic, self.mp_antibiotic_dose)
        form.addRow(self.mp_serum_pss, self.mp_serum_pgs)
        form.addRow("Доза сыворотки", self.mp_serum_dose)
        form.addRow("Анатоксин", self.mp_toxoid)
        form.addRow("Антидот", self.mp_antidote)
        form.addRow(self.mp_analgesic, self.mp_analgesic_dose)
        form.addRow(self.mp_transfusion_blood)
        form.addRow(self.mp_transfusion_substitute)
        form.addRow(self.mp_immobilization)
        form.addRow(self.mp_bandage)
        return box

    def _build_bottom_block(self) -> QWidget:
        box = QGroupBox("Нижний блок")
        form = QFormLayout(box)

        self.tourniquet_time = QTimeEdit()
        self.tourniquet_time.setDisplayFormat("HH:mm")
        self.tourniquet_time.setTime(QTime.currentTime())
        self.sanitation_type = QComboBox()
        self.sanitation_type.addItem("Полная", "full")
        self.sanitation_type.addItem("Частичная", "partial")
        self.sanitation_type.addItem("Не проводилась", "none")
        self.evacuation_dest = QComboBox()
        self.evacuation_dest.addItem("Лёжа", "lying")
        self.evacuation_dest.addItem("Сидя", "sitting")
        self.evacuation_dest.addItem("Носилки", "stretcher")
        self.evacuation_priority = QComboBox()
        self.evacuation_priority.addItem("I", "I")
        self.evacuation_priority.addItem("II", "II")
        self.evacuation_priority.addItem("III", "III")
        self.transport_type = QComboBox()
        self.transport_type.addItem("Авто", "car")
        self.transport_type.addItem("Санитарный", "ambu")
        self.transport_type.addItem("Корабль", "ship")
        self.transport_type.addItem("Вертолёт", "heli")
        self.transport_type.addItem("Самолёт", "plane")
        self.doctor_signature = QLineEdit()
        self.main_diagnosis = QTextEdit()
        self.main_diagnosis.setFixedHeight(56)

        form.addRow("Жгут (время)", self.tourniquet_time)
        form.addRow("Санобработка", self.sanitation_type)
        form.addRow("Эвакуация", self.evacuation_dest)
        form.addRow("Очередность", self.evacuation_priority)
        form.addRow("Транспорт", self.transport_type)
        form.addRow("Подпись врача", self.doctor_signature)
        form.addRow("Диагноз", self.main_diagnosis)
        return box

    def _build_flags_block(self) -> QWidget:
        box = QGroupBox("Флаг-полосы")
        grid = QGridLayout(box)
        self.flag_emergency = QCheckBox("Неотложная помощь")
        self.flag_radiation = QCheckBox("Радиационное поражение")
        self.flag_sanitation = QCheckBox("Санитарная обработка")
        grid.addWidget(self.flag_emergency, 0, 0)
        grid.addWidget(self.flag_radiation, 0, 1)
        grid.addWidget(self.flag_sanitation, 0, 2)
        return box

    def clear_form(self) -> None:
        self.current_card = None
        self.validation_banner.clear_error()

        for line in (
            self.stub_rank,
            self.stub_unit,
            self.stub_full_name,
            self.stub_id_tag,
            self.stub_antibiotic_dose,
            self.stub_pss_pgs_dose,
            self.stub_toxoid_type,
            self.stub_antidote_type,
            self.stub_analgesic_dose,
            self.main_full_name,
            self.main_unit,
            self.main_id_tag,
            self.main_rank,
            self.main_issued_place,
            self.mp_antibiotic_dose,
            self.mp_serum_dose,
            self.mp_toxoid,
            self.mp_antidote,
            self.mp_analgesic_dose,
            self.doctor_signature,
        ):
            line.clear()

        self.stub_diagnosis.clear()
        self.main_diagnosis.clear()

        today = QDate.currentDate()
        now = QTime.currentTime()
        self.stub_issued_date.setDate(today)
        self.stub_issued_time.setTime(now)
        self.stub_injury_date.setDate(today)
        self.stub_injury_time.setTime(now)
        self.birth_date.setDate(today)
        self.main_issued_date.setDate(today)
        self.main_issued_time.setTime(now)
        self.main_injury_date.setDate(today)
        self.main_injury_time.setTime(now)
        self.tourniquet_time.setTime(now)

        self.stub_evac_method.setCurrentIndex(0)
        self.stub_evac_dest.setCurrentIndex(0)
        self.sanitation_type.setCurrentIndex(0)
        self.evacuation_dest.setCurrentIndex(0)
        self.evacuation_priority.setCurrentIndex(0)
        self.transport_type.setCurrentIndex(0)

        for check in (
            self.stub_transfusion,
            self.stub_immobilization,
            self.stub_tourniquet,
            self.isolation_required,
            self.mp_antibiotic,
            self.mp_serum_pss,
            self.mp_serum_pgs,
            self.mp_analgesic,
            self.mp_transfusion_blood,
            self.mp_transfusion_substitute,
            self.mp_immobilization,
            self.mp_bandage,
            self.flag_emergency,
            self.flag_radiation,
            self.flag_sanitation,
        ):
            check.setChecked(False)
        for check in self.lesion_checks.values():
            check.setChecked(False)
        for check in self.san_loss_checks.values():
            check.setChecked(False)
        for check in self.tissue_checks.values():
            check.setChecked(False)
        for check in self.stub_med_help_checks.values():
            check.setChecked(False)
        self.bodymap_editor.clear()
    def load_card(self, card: Form100CardV2Dto) -> None:
        self.current_card = card
        self.validation_banner.clear_error()
        data = card.data
        stub = dict(data.stub)
        main = dict(data.main)
        lesion = dict(data.lesion)
        san_loss = dict(data.san_loss)
        mp = dict(data.medical_help)
        bottom = dict(data.bottom)
        flags = dict(data.flags)

        self.stub_rank.setText(str(stub.get("stub_rank") or ""))
        self.stub_unit.setText(str(stub.get("stub_unit") or ""))
        self.stub_full_name.setText(str(stub.get("stub_full_name") or card.main_full_name or ""))
        self.stub_id_tag.setText(str(stub.get("stub_id_tag") or card.main_id_tag or ""))
        _set_date_edit_from_value(self.stub_issued_date, stub.get("stub_issued_date"))
        _set_time_edit_from_value(self.stub_issued_time, stub.get("stub_issued_time"))
        _set_date_edit_from_value(self.stub_injury_date, stub.get("stub_injury_date"))
        _set_time_edit_from_value(self.stub_injury_time, stub.get("stub_injury_time"))
        self._set_combo_by_value(self.stub_evac_method, str(stub.get("stub_evacuation_method") or "airplane"))
        self._set_combo_by_value(self.stub_evac_dest, str(stub.get("stub_evacuation_dest") or "lying"))
        self.stub_antibiotic_dose.setText(str(stub.get("stub_antibiotic_dose") or ""))
        self.stub_pss_pgs_dose.setText(str(stub.get("stub_pss_pgs_dose") or ""))
        self.stub_toxoid_type.setText(str(stub.get("stub_toxoid_type") or ""))
        self.stub_antidote_type.setText(str(stub.get("stub_antidote_type") or ""))
        self.stub_analgesic_dose.setText(str(stub.get("stub_analgesic_dose") or ""))
        self.stub_transfusion.setChecked(bool(stub.get("stub_transfusion")))
        self.stub_immobilization.setChecked(bool(stub.get("stub_immobilization")))
        self.stub_tourniquet.setChecked(bool(stub.get("stub_tourniquet")))
        self.stub_diagnosis.setPlainText(str(stub.get("stub_diagnosis") or card.main_diagnosis or ""))
        selected_med_help = stub.get("stub_med_help_underline") or stub.get("stub_med_help") or []
        selected_set = {str(item) for item in selected_med_help} if isinstance(selected_med_help, list) else set()
        for label, check in self.stub_med_help_checks.items():
            check.setChecked(label in selected_set)

        self.main_full_name.setText(str(main.get("main_full_name") or card.main_full_name or ""))
        self.main_unit.setText(str(main.get("main_unit") or card.main_unit or ""))
        self.main_id_tag.setText(str(main.get("main_id_tag") or card.main_id_tag or ""))
        if card.birth_date:
            self.birth_date.setDate(QDate(card.birth_date.year, card.birth_date.month, card.birth_date.day))
        else:
            self.birth_date.setDate(QDate.currentDate())
        self.main_rank.setText(str(main.get("main_rank") or ""))
        self.main_issued_place.setText(str(main.get("main_issued_place") or ""))
        _set_date_edit_from_value(self.main_issued_date, main.get("main_issued_date"))
        _set_time_edit_from_value(self.main_issued_time, main.get("main_issued_time"))
        _set_date_edit_from_value(self.main_injury_date, main.get("main_injury_date"))
        _set_time_edit_from_value(self.main_injury_time, main.get("main_injury_time"))

        for key, check in self.lesion_checks.items():
            check.setChecked(bool(lesion.get(key)))
        for key, check in self.san_loss_checks.items():
            check.setChecked(bool(san_loss.get(key)))
        self.isolation_required.setChecked(bool(lesion.get("isolation_required")))

        for item, check in self.tissue_checks.items():
            check.setChecked(item in data.bodymap_tissue_types)
        self.bodymap_editor.set_value(gender=data.bodymap_gender, annotations=data.bodymap_annotations)

        self.mp_antibiotic.setChecked(bool(mp.get("mp_antibiotic")))
        self.mp_antibiotic_dose.setText(str(mp.get("mp_antibiotic_dose") or ""))
        self.mp_serum_pss.setChecked(bool(mp.get("mp_serum_pss")))
        self.mp_serum_pgs.setChecked(bool(mp.get("mp_serum_pgs")))
        self.mp_serum_dose.setText(str(mp.get("mp_serum_dose") or ""))
        self.mp_toxoid.setText(str(mp.get("mp_toxoid") or ""))
        self.mp_antidote.setText(str(mp.get("mp_antidote") or ""))
        self.mp_analgesic.setChecked(bool(mp.get("mp_analgesic")))
        self.mp_analgesic_dose.setText(str(mp.get("mp_analgesic_dose") or ""))
        self.mp_transfusion_blood.setChecked(bool(mp.get("mp_transfusion_blood")))
        self.mp_transfusion_substitute.setChecked(bool(mp.get("mp_transfusion_substitute")))
        self.mp_immobilization.setChecked(bool(mp.get("mp_immobilization")))
        self.mp_bandage.setChecked(bool(mp.get("mp_bandage")))

        _set_time_edit_from_value(self.tourniquet_time, bottom.get("tourniquet_time"))
        self._set_combo_by_value(self.sanitation_type, str(bottom.get("sanitation_type") or "none"))
        self._set_combo_by_value(self.evacuation_dest, str(bottom.get("evacuation_dest") or "lying"))
        self._set_combo_by_value(self.evacuation_priority, str(bottom.get("evacuation_priority") or "I"))
        self._set_combo_by_value(self.transport_type, str(bottom.get("transport_type") or "car"))
        self.doctor_signature.setText(str(bottom.get("doctor_signature") or card.signed_by or ""))
        self.main_diagnosis.setPlainText(str(bottom.get("main_diagnosis") or card.main_diagnosis or ""))

        self.flag_emergency.setChecked(bool(flags.get("flag_emergency")))
        self.flag_radiation.setChecked(bool(flags.get("flag_radiation")))
        self.flag_sanitation.setChecked(bool(flags.get("flag_sanitation")))

    def build_create_request(self) -> Form100CreateV2Request:
        payload = self._build_data_payload()
        return Form100CreateV2Request(
            main_full_name=self.main_full_name.text().strip(),
            main_unit=self.main_unit.text().strip(),
            main_id_tag=_none_if_empty(self.main_id_tag.text()),
            main_diagnosis=self.main_diagnosis.toPlainText().strip(),
            birth_date=_to_py_date(self.birth_date.date()),
            data=Form100DataV2Dto.model_validate(payload),
        )

    def build_update_request(self) -> Form100UpdateV2Request:
        payload = self._build_data_payload()
        return Form100UpdateV2Request(
            main_full_name=self.main_full_name.text().strip(),
            main_unit=self.main_unit.text().strip(),
            main_id_tag=_none_if_empty(self.main_id_tag.text()),
            main_diagnosis=self.main_diagnosis.toPlainText().strip(),
            birth_date=_to_py_date(self.birth_date.date()),
            data=Form100DataV2Dto.model_validate(payload),
        )

    def build_sign_request(self, signed_by: str | None = None) -> Form100SignV2Request:
        return Form100SignV2Request(signed_by=signed_by)

    def set_read_only(self, read_only: bool) -> None:
        for widget in (
            self.stub_issued_date,
            self.stub_issued_time,
            self.stub_rank,
            self.stub_unit,
            self.stub_full_name,
            self.stub_id_tag,
            self.stub_injury_date,
            self.stub_injury_time,
            self.stub_evac_method,
            self.stub_evac_dest,
            self.stub_antibiotic_dose,
            self.stub_pss_pgs_dose,
            self.stub_toxoid_type,
            self.stub_antidote_type,
            self.stub_analgesic_dose,
            self.stub_transfusion,
            self.stub_immobilization,
            self.stub_tourniquet,
            self.stub_diagnosis,
            self.main_full_name,
            self.main_unit,
            self.main_id_tag,
            self.birth_date,
            self.main_rank,
            self.main_issued_place,
            self.main_issued_date,
            self.main_issued_time,
            self.main_injury_date,
            self.main_injury_time,
            self.isolation_required,
            self.mp_antibiotic,
            self.mp_antibiotic_dose,
            self.mp_serum_pss,
            self.mp_serum_pgs,
            self.mp_serum_dose,
            self.mp_toxoid,
            self.mp_antidote,
            self.mp_analgesic,
            self.mp_analgesic_dose,
            self.mp_transfusion_blood,
            self.mp_transfusion_substitute,
            self.mp_immobilization,
            self.mp_bandage,
            self.tourniquet_time,
            self.sanitation_type,
            self.evacuation_dest,
            self.evacuation_priority,
            self.transport_type,
            self.doctor_signature,
            self.main_diagnosis,
            self.flag_emergency,
            self.flag_radiation,
            self.flag_sanitation,
        ):
            widget.setEnabled(not read_only)
        for check in self.lesion_checks.values():
            check.setEnabled(not read_only)
        for check in self.san_loss_checks.values():
            check.setEnabled(not read_only)
        for check in self.tissue_checks.values():
            check.setEnabled(not read_only)
        for check in self.stub_med_help_checks.values():
            check.setEnabled(not read_only)
        self.bodymap_editor.setEnabled(not read_only)

    def _build_data_payload(self) -> dict[str, Any]:
        bodymap_gender, annotations = self.bodymap_editor.get_value()
        lesion = {key: check.isChecked() for key, check in self.lesion_checks.items()}
        lesion["isolation_required"] = self.isolation_required.isChecked()
        san_loss = {key: check.isChecked() for key, check in self.san_loss_checks.items()}
        tissue_types = [name for name, check in self.tissue_checks.items() if check.isChecked()]
        stub_med_help_underline = [name for name, check in self.stub_med_help_checks.items() if check.isChecked()]
        return {
            "stub": {
                "stub_issued_date": _to_storage_date(self.stub_issued_date.date()),
                "stub_issued_time": _to_storage_time(self.stub_issued_time.time()),
                "stub_rank": self.stub_rank.text().strip(),
                "stub_unit": self.stub_unit.text().strip(),
                "stub_full_name": self.stub_full_name.text().strip(),
                "stub_id_tag": self.stub_id_tag.text().strip(),
                "stub_injury_date": _to_storage_date(self.stub_injury_date.date()),
                "stub_injury_time": _to_storage_time(self.stub_injury_time.time()),
                "stub_evacuation_method": self.stub_evac_method.currentData(),
                "stub_evacuation_dest": self.stub_evac_dest.currentData(),
                "stub_med_help_underline": stub_med_help_underline,
                "stub_med_help": stub_med_help_underline,
                "stub_antibiotic_dose": self.stub_antibiotic_dose.text().strip(),
                "stub_pss_pgs_dose": self.stub_pss_pgs_dose.text().strip(),
                "stub_toxoid_type": self.stub_toxoid_type.text().strip(),
                "stub_antidote_type": self.stub_antidote_type.text().strip(),
                "stub_analgesic_dose": self.stub_analgesic_dose.text().strip(),
                "stub_transfusion": self.stub_transfusion.isChecked(),
                "stub_immobilization": self.stub_immobilization.isChecked(),
                "stub_tourniquet": self.stub_tourniquet.isChecked(),
                "stub_diagnosis": self.stub_diagnosis.toPlainText().strip(),
            },
            "main": {
                "main_full_name": self.main_full_name.text().strip(),
                "main_unit": self.main_unit.text().strip(),
                "main_id_tag": self.main_id_tag.text().strip(),
                "main_rank": self.main_rank.text().strip(),
                "main_issued_place": self.main_issued_place.text().strip(),
                "main_issued_date": _to_storage_date(self.main_issued_date.date()),
                "main_issued_time": _to_storage_time(self.main_issued_time.time()),
                "main_injury_date": _to_storage_date(self.main_injury_date.date()),
                "main_injury_time": _to_storage_time(self.main_injury_time.time()),
                "birth_date": _to_py_date(self.birth_date.date()).isoformat(),
            },
            "lesion": lesion,
            "san_loss": san_loss,
            "bodymap_gender": bodymap_gender,
            "bodymap_annotations": [item.model_dump() for item in annotations],
            "bodymap_tissue_types": tissue_types,
            "medical_help": {
                "mp_antibiotic": self.mp_antibiotic.isChecked(),
                "mp_antibiotic_dose": self.mp_antibiotic_dose.text().strip(),
                "mp_serum_pss": self.mp_serum_pss.isChecked(),
                "mp_serum_pgs": self.mp_serum_pgs.isChecked(),
                "mp_serum_dose": self.mp_serum_dose.text().strip(),
                "mp_toxoid": self.mp_toxoid.text().strip(),
                "mp_antidote": self.mp_antidote.text().strip(),
                "mp_analgesic": self.mp_analgesic.isChecked(),
                "mp_analgesic_dose": self.mp_analgesic_dose.text().strip(),
                "mp_transfusion_blood": self.mp_transfusion_blood.isChecked(),
                "mp_transfusion_substitute": self.mp_transfusion_substitute.isChecked(),
                "mp_immobilization": self.mp_immobilization.isChecked(),
                "mp_bandage": self.mp_bandage.isChecked(),
            },
            "bottom": {
                "tourniquet_time": _to_storage_time(self.tourniquet_time.time()),
                "sanitation_type": self.sanitation_type.currentData(),
                "evacuation_dest": self.evacuation_dest.currentData(),
                "evacuation_priority": self.evacuation_priority.currentData(),
                "transport_type": self.transport_type.currentData(),
                "doctor_signature": self.doctor_signature.text().strip(),
                "main_diagnosis": self.main_diagnosis.toPlainText().strip(),
            },
            "flags": {
                "flag_emergency": self.flag_emergency.isChecked(),
                "flag_radiation": self.flag_radiation.isChecked(),
                "flag_sanitation": self.flag_sanitation.isChecked(),
            },
        }

    @staticmethod
    def _set_combo_by_value(combo: QComboBox, value: str) -> None:
        for idx in range(combo.count()):
            if str(combo.itemData(idx)) == value:
                combo.setCurrentIndex(idx)
                return
        if combo.count() > 0:
            combo.setCurrentIndex(0)

def _none_if_empty(value: str) -> str | None:
    text = value.strip()
    return text or None


def _to_py_date(value: QDate) -> date:
    return date(value.year(), value.month(), value.day())


def _to_storage_date(value: QDate) -> str:
    return value.toString("dd.MM.yyyy")


def _to_storage_time(value: QTime) -> str:
    return value.toString("HH:mm")


def _set_date_edit_from_value(widget: QDateEdit, value: object) -> None:
    if isinstance(value, date):
        widget.setDate(QDate(value.year, value.month, value.day))
        return
    text = str(value or "").strip()
    if not text:
        widget.setDate(QDate.currentDate())
        return
    for fmt in ("dd.MM.yyyy", "yyyy-MM-dd"):
        parsed = QDate.fromString(text, fmt)
        if parsed.isValid():
            widget.setDate(parsed)
            return
    widget.setDate(QDate.currentDate())


def _set_time_edit_from_value(widget: QTimeEdit, value: object) -> None:
    text = str(value or "").strip()
    if not text:
        widget.setTime(QTime.currentTime())
        return
    for fmt in ("HH:mm", "HH:mm:ss"):
        parsed = QTime.fromString(text, fmt)
        if parsed.isValid():
            widget.setTime(parsed)
            return
    widget.setTime(QTime.currentTime())
