from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date
from typing import cast

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.auth_dto import SessionContext
from app.application.dto.emz_dto import EmzCaseDetail, EmzCaseResponse
from app.application.dto.patient_dto import PatientResponse
from app.application.services.emz_service import EmzService
from app.application.services.patient_service import PatientService
from app.application.services.reference_service import ReferenceService
from app.ui.patient.emk_utils import (
    choose_latest_case_id,
    format_emk_datetime,
    format_patient_sex,
    matches_case_filters,
    normalize_filter_date,
)
from app.ui.widgets.action_bar_layout import update_action_bar_direction
from app.ui.widgets.async_task import run_async
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import clear_status, set_status
from app.ui.widgets.table_utils import resize_columns_by_first_row


class PatientEmkView(QWidget):
    def __init__(
        self,
        patient_service: PatientService,
        emz_service: EmzService,
        reference_service: ReferenceService,
        session: SessionContext | None,
        on_open_emz: Callable[[int | None, int | None], None],
        on_open_lab: Callable[[int | None, int | None], None],
        on_edit_patient: Callable[[int], None] | None = None,
        on_data_changed: Callable[[], None] | None = None,
        on_open_form100: Callable[[int | None, int | None], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.patient_service = patient_service
        self.emz_service = emz_service
        self.reference_service = reference_service
        self._session = session
        self.on_open_emz = on_open_emz
        self.on_open_lab = on_open_lab
        self.on_edit_patient = on_edit_patient
        self.on_data_changed = on_data_changed
        self.on_open_form100 = on_open_form100
        self._dept_map: dict[int, str] = {}
        self._cases_cache: list[tuple[EmzCaseDetail, EmzCaseResponse]] = []
        self._current_patient: PatientResponse | None = None
        self._current_case_id: int | None = None
        self._date_empty = QDate(2000, 1, 1)
        self._search_token = 0
        self._cases_token = 0
        self._build_ui()
        self._load_departments()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Поиск и ЭМК")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        layout.addWidget(self._build_quick_actions_row())
        layout.addWidget(self._build_search_box())

        self._content_bar = QWidget()
        self._content_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._content_bar)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(12)
        self._results_box = self._build_results_box()
        self._content_layout.addWidget(self._results_box, 1)

        self._right_panel = QWidget()
        right_col = QVBoxLayout(self._right_panel)
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(12)
        right_col.addWidget(self._build_patient_box())
        right_col.addWidget(self._build_cases_box(), 3)

        self._content_layout.addWidget(self._right_panel, 2)
        layout.addWidget(self._content_bar)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 2, 0, 0)
        self.status_label = QLabel("")
        self.status_label.setProperty("status_pill", True)
        self.status_label.setProperty("status_pill_max_width", 520)
        set_status(self.status_label, "", "info")
        self.status_label.setVisible(False)
        status_row.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        status_row.addStretch()
        layout.addLayout(status_row)
        self._update_page_layouts()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_page_layouts()

    def _build_quick_actions_row(self) -> QWidget:
        quick_emz = QPushButton("Открыть ЭМЗ")
        quick_emz.setObjectName("primaryButton")
        compact_button(quick_emz)
        quick_emz.clicked.connect(self._open_emz)
        quick_lab = QPushButton("Открыть Лаб")
        compact_button(quick_lab)
        quick_lab.clicked.connect(self._open_lab)
        quick_form100 = QPushButton("Форма 100")
        compact_button(quick_form100)
        quick_form100.clicked.connect(self._open_form100)
        quick_del_case = QPushButton("Удалить ЭМЗ")
        quick_del_case.setObjectName("secondaryButton")
        compact_button(quick_del_case)
        quick_del_case.clicked.connect(self._delete_case)
        quick_del_patient = QPushButton("Удалить пациента")
        quick_del_patient.setObjectName("secondaryButton")
        compact_button(quick_del_patient)
        quick_del_patient.clicked.connect(self._delete_patient)
        self._quick_actions_bar = QWidget()
        self._quick_actions_bar.setObjectName("sectionActionBar")
        self._quick_actions_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._quick_actions_bar)
        self._quick_actions_layout.setContentsMargins(12, 8, 12, 8)
        self._quick_actions_layout.setSpacing(10)

        self._quick_nav_group = QWidget()
        self._quick_nav_group.setObjectName("sectionActionGroup")
        nav_layout = QHBoxLayout(self._quick_nav_group)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)
        nav_layout.addWidget(quick_emz)
        nav_layout.addWidget(quick_lab)
        nav_layout.addWidget(quick_form100)

        self._quick_danger_group = QWidget()
        self._quick_danger_group.setObjectName("sectionActionGroup")
        danger_layout = QHBoxLayout(self._quick_danger_group)
        danger_layout.setContentsMargins(0, 0, 0, 0)
        danger_layout.setSpacing(8)
        danger_layout.addWidget(quick_del_case)
        danger_layout.addWidget(quick_del_patient)

        self._quick_actions_layout.addWidget(self._quick_nav_group)
        self._quick_actions_layout.addStretch()
        self._quick_actions_layout.addWidget(self._quick_danger_group)
        self._update_quick_actions_layout()
        return self._quick_actions_bar

    def _update_quick_actions_layout(self) -> None:
        update_action_bar_direction(
            self._quick_actions_layout,
            self._quick_actions_bar,
            [self._quick_nav_group, self._quick_danger_group],
        )

    def _build_search_box(self) -> QGroupBox:
        search_box = QGroupBox("Поиск пациента")
        self._search_bar = QWidget(search_box)
        self._search_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._search_bar)
        self._search_layout.setContentsMargins(0, 0, 0, 0)
        self._search_layout.setSpacing(8)

        shell_layout = QVBoxLayout(search_box)
        shell_layout.setContentsMargins(10, 8, 10, 8)
        shell_layout.setSpacing(0)
        shell_layout.addWidget(self._search_bar)

        self._search_form_group = QWidget()
        form_wrap = QVBoxLayout(self._search_form_group)
        form_wrap.setContentsMargins(0, 0, 0, 0)
        form = QFormLayout()
        self.search_name = QLineEdit()
        self.search_id = QLineEdit()
        self.search_id.setPlaceholderText("ID пациента")
        self.search_name.setPlaceholderText("ФИО пациента")
        form.addRow("ФИО", self.search_name)
        form.addRow("ID", self.search_id)
        form_wrap.addLayout(form)
        self._search_layout.addWidget(self._search_form_group, 1)

        self._search_actions_group = QWidget()
        actions_layout = QHBoxLayout(self._search_actions_group)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        self.search_btn = QPushButton("Поиск")
        self.search_btn.setObjectName("primaryButton")
        compact_button(self.search_btn)
        self.search_btn.clicked.connect(self._run_search)
        self.reset_btn = QPushButton("Сбросить")
        compact_button(self.reset_btn)
        self.reset_btn.clicked.connect(self._reset_search)
        actions_layout.addWidget(self.search_btn)
        actions_layout.addWidget(self.reset_btn)
        self._search_layout.addWidget(self._search_actions_group)
        self._update_search_layout()
        return search_box

    def _update_page_layouts(self) -> None:
        if hasattr(self, "_quick_actions_layout"):
            self._update_quick_actions_layout()
        if hasattr(self, "_search_layout"):
            self._update_search_layout()
        if hasattr(self, "_content_layout"):
            self._update_content_layout()

    def _update_search_layout(self) -> None:
        update_action_bar_direction(
            self._search_layout,
            self._search_bar,
            [self._search_form_group, self._search_actions_group],
        )

    def _update_content_layout(self) -> None:
        update_action_bar_direction(
            self._content_layout,
            self._content_bar,
            [self._results_box, self._right_panel],
            extra_width=18,
        )

    def _build_results_box(self) -> QGroupBox:
        results_box = QGroupBox("Результаты поиска")
        results_layout = QVBoxLayout(results_box)
        self.results_list = QListWidget()
        self.results_list.itemSelectionChanged.connect(self._select_from_results)
        self.results_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self._show_patient_menu)
        results_layout.addWidget(self.results_list)
        return results_box

    def _build_patient_box(self) -> QGroupBox:
        patient_box = QGroupBox("Карточка пациента")
        patient_box.setObjectName("patientCard")
        patient_layout = QVBoxLayout(patient_box)
        patient_layout.setSpacing(10)

        self.label_full_name = QLabel("—")
        self.label_full_name.setObjectName("patientName")
        self.label_full_name.setWordWrap(True)
        patient_layout.addWidget(self.label_full_name)

        self.patient_subtitle = QLabel("Выберите пациента для просмотра структурированных данных.")
        self.patient_subtitle.setObjectName("patientSubtitle")
        self.patient_subtitle.setWordWrap(True)
        patient_layout.addWidget(self.patient_subtitle)

        id_row = QHBoxLayout()
        self._id_card = QWidget()
        self._id_card.setObjectName("patientIdCard")
        id_card_layout = QVBoxLayout(self._id_card)
        id_card_layout.setContentsMargins(10, 6, 10, 6)
        id_card_layout.setSpacing(2)
        id_caption = QLabel("Идентификатор пациента")
        id_caption.setObjectName("patientIdCaption")
        self.label_patient_id = QLabel("—")
        self.label_patient_id.setObjectName("patientIdBadge")
        id_card_layout.addWidget(id_caption)
        id_card_layout.addWidget(self.label_patient_id)
        id_row.addWidget(self._id_card)
        id_row.addStretch()
        patient_layout.addLayout(id_row)

        separator = QWidget()
        separator.setObjectName("patientSeparator")
        separator.setFixedHeight(1)
        patient_layout.addWidget(separator)

        grid = QGridLayout()
        grid.setContentsMargins(0, 2, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        def add_field(row: int, col: int, title: str, col_span: int = 1) -> QLabel:
            card = QWidget()
            card.setObjectName("patientFieldCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 7, 10, 7)
            card_layout.setSpacing(2)
            title_label = QLabel(title)
            title_label.setObjectName("patientFieldTitle")
            value_label = QLabel("—")
            value_label.setObjectName("patientFieldValue")
            value_label.setWordWrap(True)
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            grid.addWidget(card, row, col, 1, col_span)
            return value_label

        self.label_dob = add_field(0, 0, "Дата рождения")
        self.label_sex = add_field(0, 1, "Пол")
        self.label_category = add_field(1, 0, "Категория", 2)
        self.label_military_unit = add_field(2, 0, "Воинская часть")
        self.label_military_district = add_field(2, 1, "Военный округ")
        patient_layout.addLayout(grid)

        edit_row = QHBoxLayout()
        edit_row.addStretch()
        self.edit_patient_btn = QPushButton("Редактировать пациента")
        self.edit_patient_btn.setObjectName("primaryButton")
        compact_button(self.edit_patient_btn)
        self.edit_patient_btn.clicked.connect(self._open_edit_patient)
        self.edit_patient_btn.setEnabled(False)
        edit_row.addWidget(self.edit_patient_btn)
        patient_layout.addLayout(edit_row)
        return patient_box

    def _build_case_filters_row(self) -> QHBoxLayout:
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        filter_row.addWidget(QLabel("Отделение"))
        self.department_filter = QComboBox()
        self.department_filter.addItem("Все отделения", None)
        self.department_filter.currentIndexChanged.connect(self._apply_case_filters)
        filter_row.addWidget(self.department_filter)
        filter_row.addWidget(QLabel("Период"))
        self.date_from = QDateEdit()
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setCalendarPopup(True)
        self.date_from.setSpecialValueText("")
        self.date_from.setDate(self._date_empty)
        self.date_from.setMinimumDate(self._date_empty)
        self.date_to = QDateEdit()
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setCalendarPopup(True)
        self.date_to.setSpecialValueText("")
        self.date_to.setDate(self._date_empty)
        self.date_to.setMinimumDate(self._date_empty)
        self.date_from.dateChanged.connect(self._apply_case_filters)
        self.date_to.dateChanged.connect(self._apply_case_filters)
        filter_row.addWidget(self.date_from)
        filter_row.addWidget(QLabel("по"))
        filter_row.addWidget(self.date_to)
        reset_filters = QPushButton("Сбросить фильтры")
        compact_button(reset_filters)
        reset_filters.clicked.connect(self._reset_filters)
        filter_row.addWidget(reset_filters)
        filter_row.addStretch()
        return filter_row

    def _build_cases_box(self) -> QGroupBox:
        cases_box = QGroupBox("Госпитализации")
        cases_layout = QVBoxLayout(cases_box)
        cases_layout.addLayout(self._build_case_filters_row())
        self.cases_empty_label = QLabel("У пациента нет госпитализаций. Создайте ЭМЗ.")
        self.cases_empty_label.setObjectName("muted")
        self.cases_empty_label.setWordWrap(True)
        self.cases_empty_label.setVisible(False)
        cases_layout.addWidget(self.cases_empty_label)
        self.cases_table = QTableWidget(0, 6)
        self.cases_table.setHorizontalHeaderLabels(
            [
                "№ карты пациента",
                "Отделение",
                "Дата поступления",
                "Дата исхода",
                "Статус",
                "№ госпитализации",
            ]
        )
        self.cases_table.setAlternatingRowColors(True)
        self.cases_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cases_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cases_table.horizontalHeader().setStretchLastSection(True)
        self.cases_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cases_table.customContextMenuRequested.connect(self._show_case_menu)
        self.cases_table.itemSelectionChanged.connect(self._on_case_selected)
        self.cases_table.setProperty(
            "min_column_widths",
            {0: 160, 1: 160, 2: 160, 3: 140, 4: 120, 5: 150},
        )
        cases_layout.addWidget(self.cases_table)
        return cases_box

    def _set_status(self, message: str, level: str = "info") -> None:
        if not message:
            clear_status(self.status_label)
            self.status_label.setVisible(False)
            return
        self.status_label.setVisible(True)
        set_status(self.status_label, message, level)

    def _open_edit_patient(self) -> None:
        if not self._current_patient:
            self._set_status("Сначала выберите пациента.", "warning")
            return
        if self.on_edit_patient:
            self.on_edit_patient(self._current_patient.id)

    def _reset_search(self) -> None:
        self._search_token += 1
        self.search_name.clear()
        self.search_id.clear()
        self.results_list.clear()
        self._clear_patient()
        self._set_status("")
        self._set_search_busy(False)

    def _set_search_busy(self, busy: bool) -> None:
        self.search_btn.setEnabled(not busy)
        self.reset_btn.setEnabled(not busy)

    def _run_search(self) -> None:
        self._set_status("")
        query_id = self.search_id.text().strip()
        query_name = self.search_name.text().strip()
        self.results_list.clear()

        if query_id:
            try:
                patient_id = int(query_id)
            except ValueError:
                self._set_status("ID пациента должен быть числом", "warning")
                self._set_search_busy(False)
                return
            try:
                patient = self.patient_service.get_by_id(patient_id)
            except Exception as exc:  # noqa: BLE001
                self._set_status(f"Не удалось найти пациента: {exc}", "warning")
                self._set_search_busy(False)
                return
            self._add_patient_result(patient)
            if self.results_list.count() > 0:
                self.results_list.setCurrentRow(0)
            self._set_patient(patient)
            self._load_cases(patient.id)
            self._set_status("Пациент найден", "success")
            self._set_search_busy(False)
            return

        if not query_name:
            self._set_status("Укажите ФИО или ID пациента", "warning")
            self._set_search_busy(False)
            return

        self._search_token += 1
        token = self._search_token
        self._set_search_busy(True)

        def _run() -> list[PatientResponse]:
            return self.patient_service.search_by_name(query_name, limit=50)

        def _on_success(patients: list[PatientResponse]) -> None:
            if token != self._search_token:
                return
            if not patients:
                self._set_status("Пациенты не найдены", "warning")
                self._set_search_busy(False)
                return
            for patient in patients:
                self._add_patient_result(patient)
            self._set_status(f"Найдено: {len(patients)}", "success")
            self._set_search_busy(False)

        def _on_error(exc: Exception) -> None:
            if token != self._search_token:
                return
            self._set_status(f"Ошибка поиска: {exc}", "error")
            self._set_search_busy(False)

        run_async(
            self,
            _run,
            on_success=_on_success,
            on_error=_on_error,
            on_finished=lambda: self._set_search_busy(False),
        )

    def _add_patient_result(self, patient: PatientResponse) -> None:
        dob_text = patient.dob.strftime("%d.%m.%Y") if patient.dob else ""
        label = f"{patient.full_name}"
        if dob_text:
            label = f"{label} ({dob_text})"
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, patient.id)
        self.results_list.addItem(item)

    def _select_from_results(self) -> None:
        items = self.results_list.selectedItems()
        if not items:
            return
        patient_id = items[0].data(Qt.ItemDataRole.UserRole)
        if patient_id is None:
            return
        patient = self.patient_service.get_by_id(int(patient_id))
        self._set_patient(patient)
        self._load_cases(patient.id)

    def _set_patient(self, patient: PatientResponse) -> None:
        self._current_patient = patient
        self.label_full_name.setText(patient.full_name)
        self.patient_subtitle.setText("Основные данные пациента в едином карточном формате.")
        self.label_patient_id.setText(f"#{patient.id}")
        self.label_dob.setText(patient.dob.strftime("%d.%m.%Y") if patient.dob else "—")
        self.label_sex.setText(format_patient_sex(patient.sex))
        self.label_category.setText(patient.category or "—")
        self.label_military_unit.setText(patient.military_unit or "—")
        self.label_military_district.setText(patient.military_district or "—")
        if hasattr(self, "edit_patient_btn"):
            self.edit_patient_btn.setEnabled(True)

    def _clear_patient(self) -> None:
        self._current_patient = None
        self._current_case_id = None
        self._cases_cache = []
        self.label_full_name.setText("—")
        self.patient_subtitle.setText("Выберите пациента для просмотра структурированных данных.")
        self.label_patient_id.setText("—")
        self.label_dob.setText("—")
        self.label_sex.setText("—")
        self.label_category.setText("—")
        self.label_military_unit.setText("—")
        self.label_military_district.setText("—")
        if hasattr(self, "edit_patient_btn"):
            self.edit_patient_btn.setEnabled(False)
        self.cases_table.setRowCount(0)
        if hasattr(self, "cases_empty_label"):
            self.cases_empty_label.setVisible(False)

    def refresh_references(self) -> None:
        self._load_departments()
        if self._current_patient:
            self._load_cases(self._current_patient.id)

    def set_session(self, session: SessionContext) -> None:
        self._session = session

    def clear_context(self) -> None:
        self.search_name.clear()
        self.search_id.clear()
        self.results_list.clear()
        self._clear_patient()
        self._set_status("")

    def set_context(self, patient_id: int | None, emr_case_id: int | None) -> None:
        if patient_id is None:
            self.clear_context()
            return
        try:
            patient = self.patient_service.get_by_id(patient_id)
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Не удалось загрузить пациента: {exc}", "warning")
            return
        self._set_patient(patient)
        self._load_cases(patient_id)
        self._select_case_by_id(emr_case_id)

    def refresh_patient(self, patient_id: int) -> None:
        self.set_context(patient_id, self._current_case_id)

    def _load_departments(self) -> None:
        try:
            self.department_filter.clear()
            self.department_filter.addItem("Все отделения", None)
            self._dept_map.clear()
            for dep in self.reference_service.list_departments():
                dep_id = cast(int, dep.id)
                dep_name = str(dep.name)
                self._dept_map[dep_id] = dep_name
                self.department_filter.addItem(dep_name, dep_id)
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).warning("Failed to load departments: %s", exc)

    def _load_cases(self, patient_id: int) -> None:
        self._cases_cache = []
        current_dep = self.department_filter.currentData() if hasattr(self, "department_filter") else None
        self._load_departments()
        if current_dep is not None:
            idx = self.department_filter.findData(current_dep)
            if idx >= 0:
                self.department_filter.setCurrentIndex(idx)

        self._set_status("Загрузка госпитализаций...", "info")
        try:
            cases = self.emz_service.list_cases_by_patient(patient_id)
            self._cases_cache = [(self.emz_service.get_current(case.id), case) for case in cases]
            self._apply_case_filters()
            self._set_status("")
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Не удалось загрузить госпитализации: {exc}", "error")

    def _reset_filters(self) -> None:
        self.department_filter.setCurrentIndex(0)
        self.date_from.setDate(self._date_empty)
        self.date_to.setDate(self._date_empty)
        self._apply_case_filters()

    def _apply_case_filters(self) -> None:
        department_id = self.department_filter.currentData()
        from_date_raw = self.date_from.date().toPython()
        to_date_raw = self.date_to.date().toPython()
        from_date = cast(date, from_date_raw) if isinstance(from_date_raw, date) else None
        to_date = cast(date, to_date_raw) if isinstance(to_date_raw, date) else None
        empty_date_raw = self._date_empty.toPython()
        empty_date = cast(date, empty_date_raw) if isinstance(empty_date_raw, date) else date(2000, 1, 1)
        from_date = normalize_filter_date(from_date, empty_date)
        to_date = normalize_filter_date(to_date, empty_date)
        self.cases_table.setRowCount(0)
        self._current_case_id = None

        for detail, resp in self._cases_cache:
            if not matches_case_filters(detail, department_id, from_date, to_date):
                continue

            row = self.cases_table.rowCount()
            self.cases_table.insertRow(row)
            self._set_case_row(row, detail, resp)

        resize_columns_by_first_row(self.cases_table)
        if not self._current_patient:
            self.cases_empty_label.setVisible(False)
        elif not self._cases_cache:
            self.cases_empty_label.setText("У пациента нет госпитализаций. Создайте ЭМЗ.")
            self.cases_empty_label.setVisible(True)
        elif self.cases_table.rowCount() == 0:
            self.cases_empty_label.setText("Госпитализации не найдены по текущим фильтрам.")
            self.cases_empty_label.setVisible(True)
        else:
            self.cases_empty_label.setVisible(False)

    def _set_case_row(self, row: int, detail: EmzCaseDetail, resp: EmzCaseResponse) -> None:
        case_no = detail.hospital_case_no or "—"
        department = self._dept_map.get(detail.department_id or 0, "—")
        admission = format_emk_datetime(detail.admission_date)
        outcome = format_emk_datetime(detail.outcome_date)
        status = "текущая" if resp.is_current else "архив"
        values = [case_no, department, admission, outcome, status, str(detail.id)]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if col == 0:
                item.setData(Qt.ItemDataRole.UserRole, detail.id)
            self.cases_table.setItem(row, col, item)

    def _on_case_selected(self) -> None:
        items = self.cases_table.selectedItems()
        if not items:
            self._current_case_id = None
            return
        case_id = items[0].data(Qt.ItemDataRole.UserRole)
        self._current_case_id = int(case_id) if case_id is not None else None

    def _select_case_by_id(self, emr_case_id: int | None) -> None:
        if emr_case_id is None:
            self.cases_table.clearSelection()
            self._current_case_id = None
            return
        for row in range(self.cases_table.rowCount()):
            item = self.cases_table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == emr_case_id:
                self.cases_table.selectRow(row)
                self._current_case_id = emr_case_id
                return
        self.cases_table.clearSelection()
        self._current_case_id = None

    def _choose_latest_case_id(self) -> int | None:
        return choose_latest_case_id(self._cases_cache)

    def _open_form100(self) -> None:
        if not self._current_patient:
            self._set_status("Выберите пациента.", "warning")
            return
        case_id = self._current_case_id
        if case_id is None:
            case_id = self._choose_latest_case_id()
        if self.on_open_form100:
            self.on_open_form100(self._current_patient.id, case_id)

    def _open_emz(self) -> None:
        if not self._current_patient:
            self._set_status("Выберите пациента.", "warning")
            return
        case_id = self._current_case_id
        if case_id is None:
            case_id = self._choose_latest_case_id()
        if case_id is None:
            self._set_status("Нет госпитализаций для выбранного пациента.", "warning")
            return
        self.on_open_emz(self._current_patient.id, case_id)

    def _open_lab(self) -> None:
        if not self._current_patient:
            self._set_status("Выберите пациента.", "warning")
            return
        self.on_open_lab(self._current_patient.id, self._current_case_id)

    def _show_case_menu(self, pos) -> None:
        if not self._current_patient:
            return
        menu = QMenu(self)
        delete_action = menu.addAction("Удалить ЭМЗ")
        chosen = menu.exec(self.cases_table.viewport().mapToGlobal(pos))
        if chosen == delete_action:
            self._delete_case()

    def _show_patient_menu(self, pos) -> None:
        if not self._current_patient:
            return
        menu = QMenu(self)
        delete_action = menu.addAction("Удалить пациента")
        chosen = menu.exec(self.results_list.viewport().mapToGlobal(pos))
        if chosen == delete_action:
            self._delete_patient()

    def _delete_case(self) -> None:
        if not self._current_patient or self._current_case_id is None:
            self._set_status("Выберите госпитализацию.", "warning")
            return
        case_no = "—"
        for detail, _resp in self._cases_cache:
            if detail.id == self._current_case_id:
                case_no = detail.hospital_case_no or "—"
                break
        confirm = QMessageBox.question(
            self,
            "Удалить ЭМЗ",
            f"Удалить ЭМЗ пациента {self._current_patient.full_name}\n"
            f"(госпитализация №{case_no})?\n"
            "Данные будут удалены без возможности восстановления.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            actor_id = self._session.user_id if self._session is not None else None
            self.emz_service.delete_emr(self._current_case_id, actor_id=actor_id)
            self._current_case_id = None
            self._load_cases(self._current_patient.id)
            self._set_status("ЭМЗ удалена", "success")
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Ошибка: {exc}", "error")

    def _delete_patient(self) -> None:
        if not self._current_patient:
            self._set_status("Выберите пациента.", "warning")
            return
        confirm = QMessageBox.question(
            self,
            "Удалить пациента",
            f"Удалить пациента {self._current_patient.full_name}?\n"
            "Все данные будут удалены без возможности восстановления.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            patient_id = self._current_patient.id
            self.patient_service.delete_patient(patient_id)
            self._reset_search()
            self._set_status("Пациент удалён", "success")
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Ошибка: {exc}", "error")
