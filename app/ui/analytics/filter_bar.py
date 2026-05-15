from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QDate, QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.domain.constants import MilitaryCategory
from app.ui.analytics.view_utils import (
    make_section_frame,
    normalize_date_range,
    quick_period_bounds,
)
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.table_utils import connect_combo_autowidth

if TYPE_CHECKING:
    from app.application.services.reference_service import ReferenceService


class FilterBar(QWidget):
    filters_changed = Signal(object)

    def __init__(self, reference_service: ReferenceService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.reference_service = reference_service
        self._advanced_visible = False
        self._build_ui()
        self.reload_references()
        self._initialize_default_period()
        self._connect_change_signals()

    def request(self) -> AnalyticsSearchRequest:
        date_from = cast(date | None, self.date_from.date().toPython())
        date_to = cast(date | None, self.date_to.date().toPython())
        date_from, date_to = normalize_date_range(date_from, date_to)
        return AnalyticsSearchRequest(
            date_from=date_from,
            date_to=date_to,
            department_id=self.department.currentData(),
            icd10_code=self.icd10.currentData(),
            microorganism_id=self.microbe.currentData(),
            antibiotic_id=self.antibiotic.currentData(),
            material_type_id=self.material.currentData(),
            growth_flag=self.growth_flag.currentData(),
            patient_category=self.patient_category.currentData(),
            patient_name=self.patient_name.text().strip() or None,
            lab_no=self.lab_no.text().strip() or None,
            search_text=self.search_text.text().strip() or None,
        )

    def request_payload(self) -> dict[str, object]:
        request = self.request()
        payload = request.model_dump(exclude_none=True)
        if request.date_from is not None:
            payload["date_from"] = request.date_from.strftime("%d.%m.%Y")
        if request.date_to is not None:
            payload["date_to"] = request.date_to.strftime("%d.%m.%Y")
        return payload

    def set_request_payload(self, payload: dict[str, object]) -> None:
        blockers = [
            QSignalBlocker(self.date_from),
            QSignalBlocker(self.date_to),
            QSignalBlocker(self.department),
            QSignalBlocker(self.icd10),
            QSignalBlocker(self.microbe),
            QSignalBlocker(self.antibiotic),
            QSignalBlocker(self.material),
            QSignalBlocker(self.growth_flag),
            QSignalBlocker(self.patient_category),
            QSignalBlocker(self.patient_name),
            QSignalBlocker(self.lab_no),
            QSignalBlocker(self.search_text),
        ]
        _ = blockers
        self._set_date_from_payload(payload.get("date_from"))
        self._set_date_to_payload(payload.get("date_to"))
        self._set_combo_data(self.department, payload.get("department_id"))
        self._set_combo_data(self.icd10, payload.get("icd10_code"))
        self._set_combo_data(self.microbe, payload.get("microorganism_id"))
        self._set_combo_data(self.antibiotic, payload.get("antibiotic_id"))
        self._set_combo_data(self.material, payload.get("material_type_id"))
        self._set_combo_data(self.growth_flag, payload.get("growth_flag"))
        self._set_combo_data(self.patient_category, payload.get("patient_category"))
        self.patient_name.setText(str(payload.get("patient_name") or ""))
        self.lab_no.setText(str(payload.get("lab_no") or ""))
        self.search_text.setText(str(payload.get("search_text") or ""))
        self._emit_filters_changed()

    def reload_references(self) -> None:
        self._reload_department()
        self._reload_icd10()
        self._reload_microbes()
        self._reload_antibiotics()
        self._reload_materials()
        self._reload_growth_flag()
        self._reload_patient_category()
        for combo in (
            self.quick_period,
            self.department,
            self.icd10,
            self.microbe,
            self.antibiotic,
            self.material,
            self.growth_flag,
            self.patient_category,
        ):
            connect_combo_autowidth(combo)

    def reset_filters(self) -> None:
        blockers = [
            QSignalBlocker(self.department),
            QSignalBlocker(self.icd10),
            QSignalBlocker(self.microbe),
            QSignalBlocker(self.antibiotic),
            QSignalBlocker(self.material),
            QSignalBlocker(self.growth_flag),
            QSignalBlocker(self.patient_category),
            QSignalBlocker(self.patient_name),
            QSignalBlocker(self.lab_no),
            QSignalBlocker(self.search_text),
        ]
        _ = blockers
        self.department.setCurrentIndex(0)
        self.icd10.setCurrentIndex(0)
        self.microbe.setCurrentIndex(0)
        self.antibiotic.setCurrentIndex(0)
        self.material.setCurrentIndex(0)
        self.growth_flag.setCurrentIndex(0)
        self.patient_category.setCurrentIndex(0)
        self.patient_name.clear()
        self.lab_no.clear()
        self.search_text.clear()
        self._apply_quick_period(emit=False)
        self._emit_filters_changed()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.filters_box, filters_layout = make_section_frame("Параметры поиска")
        filters_layout.setSpacing(10)
        filters_layout.addLayout(self._build_quick_period_row())
        filters_layout.addLayout(self._build_primary_grid())

        self.advanced_container = QWidget()
        advanced_layout = QGridLayout(self.advanced_container)
        advanced_layout.setHorizontalSpacing(12)
        advanced_layout.setVerticalSpacing(10)
        self._add_advanced_fields(advanced_layout)
        self.advanced_container.setVisible(False)
        filters_layout.addWidget(self.advanced_container)

        layout.addWidget(self.filters_box)

    def _build_quick_period_row(self) -> QHBoxLayout:
        quick_row = QHBoxLayout()
        self.quick_period = QComboBox()
        self.quick_period.addItem("Сегодня", "today")
        self.quick_period.addItem("Последние 7 дней", "7d")
        self.quick_period.addItem("Последние 30 дней", "30d")
        self.quick_period.addItem("Последние 90 дней", "90d")
        self.quick_period.addItem("Текущий месяц", "month")
        self.quick_period.addItem("Текущий квартал", "quarter")

        quick_apply_btn = QPushButton("Применить период")
        compact_button(quick_apply_btn)
        quick_apply_btn.clicked.connect(self._apply_quick_period)

        self.advanced_toggle = QPushButton("Расширенный фильтр ▾")
        self.advanced_toggle.setCheckable(True)
        compact_button(self.advanced_toggle)
        self.advanced_toggle.toggled.connect(self._toggle_advanced)

        reset_filters_btn = QPushButton("Сбросить фильтры")
        compact_button(reset_filters_btn)
        reset_filters_btn.clicked.connect(self.reset_filters)

        quick_row.addWidget(QLabel("Быстрый период"))
        quick_row.addWidget(self.quick_period)
        quick_row.addWidget(quick_apply_btn)
        quick_row.addWidget(self.advanced_toggle)
        quick_row.addStretch()
        quick_row.addWidget(reset_filters_btn)
        return quick_row

    def _build_primary_grid(self) -> QGridLayout:
        self._init_filter_widgets()
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.addWidget(QLabel("Дата от"), 0, 0)
        grid.addWidget(self.date_from, 0, 1)
        grid.addWidget(QLabel("Дата по"), 0, 2)
        grid.addWidget(self.date_to, 0, 3)
        grid.addWidget(QLabel("Категория пациента"), 1, 0)
        grid.addWidget(self.patient_category, 1, 1)
        grid.addWidget(QLabel("Пациент (ФИО)"), 1, 2)
        grid.addWidget(self.patient_name, 1, 3)
        grid.addWidget(QLabel("Номер пробы"), 2, 0)
        grid.addWidget(self.lab_no, 2, 1)
        grid.addWidget(QLabel("Полнотекстовый поиск"), 2, 2)
        grid.addWidget(self.search_text, 2, 3)
        return grid

    def _add_advanced_fields(self, grid: QGridLayout) -> None:
        grid.addWidget(QLabel("Отделение"), 0, 0)
        grid.addWidget(self.department, 0, 1)
        grid.addWidget(QLabel("МКБ-10"), 0, 2)
        grid.addWidget(self.icd10, 0, 3)
        grid.addWidget(QLabel("Микроорганизм"), 1, 0)
        grid.addWidget(self.microbe, 1, 1)
        grid.addWidget(QLabel("Антибиотик"), 1, 2)
        grid.addWidget(self.antibiotic, 1, 3)
        grid.addWidget(QLabel("Материал"), 2, 0)
        grid.addWidget(self.material, 2, 1)
        grid.addWidget(QLabel("Рост"), 2, 2)
        grid.addWidget(self.growth_flag, 2, 3)

    def _init_filter_widgets(self) -> None:
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setMinimumDate(QDate(2000, 1, 1))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setMinimumDate(QDate(2000, 1, 1))
        self.department = QComboBox()
        self.icd10 = QComboBox()
        self.icd10.setEditable(True)
        self.icd10.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.microbe = QComboBox()
        self.microbe.setEditable(True)
        self.microbe.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.antibiotic = QComboBox()
        self.antibiotic.setEditable(True)
        self.antibiotic.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.material = QComboBox()
        self.material.setEditable(True)
        self.material.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.growth_flag = QComboBox()
        self.patient_category = QComboBox()
        self.patient_name = QLineEdit()
        self.patient_name.setPlaceholderText("ФИО")
        self.lab_no = QLineEdit()
        self.lab_no.setPlaceholderText("например, MAT-20250101-0001")
        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Поиск по ФИО/МКБ/микроорганизмам")

    def _connect_change_signals(self) -> None:
        self.quick_period.currentIndexChanged.connect(lambda _index: self._apply_quick_period())
        self.date_from.dateChanged.connect(lambda _date: self._emit_filters_changed())
        self.date_to.dateChanged.connect(lambda _date: self._emit_filters_changed())
        for combo in (
            self.department,
            self.icd10,
            self.microbe,
            self.antibiotic,
            self.material,
            self.growth_flag,
            self.patient_category,
        ):
            combo.currentIndexChanged.connect(lambda _index: self._emit_filters_changed())
        self.patient_name.textChanged.connect(lambda _text: self._emit_filters_changed())
        self.lab_no.textChanged.connect(lambda _text: self._emit_filters_changed())
        self.search_text.textChanged.connect(lambda _text: self._emit_filters_changed())

    def _initialize_default_period(self) -> None:
        month_index = self.quick_period.findData("month")
        if month_index >= 0:
            with QSignalBlocker(self.quick_period):
                self.quick_period.setCurrentIndex(month_index)
        self._apply_quick_period(emit=False)

    def _apply_quick_period(self, emit: bool = True) -> None:
        today_qdate = QDate.currentDate()
        today = cast(date, today_qdate.toPython())
        mode = cast(str | None, self.quick_period.currentData())
        date_from, date_to = self._quick_period_bounds(mode, today)
        with QSignalBlocker(self.date_from), QSignalBlocker(self.date_to):
            self.date_from.setDate(QDate(date_from.year, date_from.month, date_from.day))
            self.date_to.setDate(QDate(date_to.year, date_to.month, date_to.day))
        if emit:
            self._emit_filters_changed()

    def _quick_period_bounds(self, mode: str | None, today: date) -> tuple[date, date]:
        if mode == "quarter":
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            return date(today.year, quarter_month, 1), today
        return quick_period_bounds(mode, today)

    def _toggle_advanced(self, checked: bool) -> None:
        self._advanced_visible = checked
        self.advanced_container.setVisible(checked)
        self.advanced_toggle.setText("Расширенный фильтр ▴" if checked else "Расширенный фильтр ▾")

    def _emit_filters_changed(self) -> None:
        self.filters_changed.emit(self.request())

    def _reload_department(self) -> None:
        current = self.department.currentData()
        with QSignalBlocker(self.department):
            self.department.clear()
            self.department.addItem("Выбрать", None)
            for dep in self.reference_service.list_departments():
                self.department.addItem(str(dep.name), cast(int, dep.id))
            self._set_combo_data(self.department, current)

    def _reload_icd10(self) -> None:
        current = self.icd10.currentData()
        with QSignalBlocker(self.icd10):
            self.icd10.clear()
            self.icd10.addItem("Выбрать", None)
            for icd in self.reference_service.list_icd10():
                self.icd10.addItem(f"{icd.code} - {icd.title}", str(icd.code))
            self._set_combo_data(self.icd10, current)

    def _reload_microbes(self) -> None:
        current = self.microbe.currentData()
        with QSignalBlocker(self.microbe):
            self.microbe.clear()
            self.microbe.addItem("Выбрать", None)
            for micro in self.reference_service.list_microorganisms():
                self.microbe.addItem(f"{micro.code or '-'} - {micro.name}", cast(int, micro.id))
            self._set_combo_data(self.microbe, current)

    def _reload_antibiotics(self) -> None:
        current = self.antibiotic.currentData()
        with QSignalBlocker(self.antibiotic):
            self.antibiotic.clear()
            self.antibiotic.addItem("Выбрать", None)
            for antibiotic in self.reference_service.list_antibiotics():
                self.antibiotic.addItem(f"{antibiotic.code} - {antibiotic.name}", cast(int, antibiotic.id))
            self._set_combo_data(self.antibiotic, current)

    def _reload_materials(self) -> None:
        current = self.material.currentData()
        with QSignalBlocker(self.material):
            self.material.clear()
            self.material.addItem("Выбрать", None)
            for material in self.reference_service.list_material_types():
                self.material.addItem(f"{material.code} - {material.name}", cast(int, material.id))
            self._set_combo_data(self.material, current)

    def _reload_growth_flag(self) -> None:
        current = self.growth_flag.currentData()
        with QSignalBlocker(self.growth_flag):
            self.growth_flag.clear()
            self.growth_flag.addItem("Выбрать", None)
            self.growth_flag.addItem("Нет", 0)
            self.growth_flag.addItem("Да", 1)
            self._set_combo_data(self.growth_flag, current)

    def _reload_patient_category(self) -> None:
        current = self.patient_category.currentData()
        with QSignalBlocker(self.patient_category):
            self.patient_category.clear()
            self.patient_category.addItem("Выбрать", None)
            for value in MilitaryCategory.values():
                self.patient_category.addItem(value, value)
            self._set_combo_data(self.patient_category, current)

    def _set_date_from_payload(self, value: object) -> None:
        qdate = self._parse_payload_date(value)
        if qdate is not None:
            self.date_from.setDate(qdate)

    def _set_date_to_payload(self, value: object) -> None:
        qdate = self._parse_payload_date(value)
        if qdate is not None:
            self.date_to.setDate(qdate)

    def _parse_payload_date(self, value: object) -> QDate | None:
        if not value:
            return None
        if isinstance(value, date):
            return QDate(value.year, value.month, value.day)
        qdate = QDate.fromString(str(value), "dd.MM.yyyy")
        if not qdate.isValid():
            qdate = QDate.fromString(str(value), "yyyy-MM-dd")
        return qdate if qdate.isValid() else None

    def _set_combo_data(self, combo: QComboBox, value: object) -> None:
        if value is None:
            combo.setCurrentIndex(0 if combo.count() else -1)
            return
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
