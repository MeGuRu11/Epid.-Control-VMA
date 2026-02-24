from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import Any, cast

from PySide6.QtCore import QDate, QDateTime, Qt, QTime
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.emz_dto import (
    EmzAntibioticCourseDto,
    EmzCaseDetail,
    EmzDiagnosisDto,
    EmzInterventionDto,
    EmzIsmpDto,
    EmzVersionPayload,
)
from app.container import Container
from app.domain.constants import MilitaryCategory
from app.ui.emz.form_case_selectors import pick_latest_case_id
from app.ui.emz.form_field_resolvers import (
    normalize_sex_label,
    parse_optional_int,
    resolve_department_id,
)
from app.ui.emz.form_icd_search import (
    refresh_icd_combo,
    wire_icd_search,
)
from app.ui.emz.form_mode_presenters import (
    build_edit_mode_ui_state,
    build_new_case_access_state,
    patient_hint_for_read_only,
)
from app.ui.emz.form_orchestrators import (
    LoadCaseContext,
    collect_save_case_context,
    run_load_case,
    run_save_case,
)
from app.ui.emz.form_patient_identity import (
    PatientIdentityData,
    identity_from_case_detail,
    identity_from_patient_record,
)
from app.ui.emz.form_presenters import (
    format_save_message,
    int_or_empty,
    split_date_or_datetime,
    text_or_empty,
)
from app.ui.emz.form_reference_orchestrators import (
    apply_departments_to_combo,
    refresh_detail_reference_rows,
    restore_department_selection,
    setup_abx_reference_rows,
    setup_detail_reference_rows,
    setup_diagnosis_reference_rows,
    setup_ismp_reference_rows,
)
from app.ui.emz.form_request_builders import (
    build_emz_create_request,
    build_emz_update_request,
    build_emz_version_payload,
    build_patient_update_fields,
)
from app.ui.emz.form_table_actions import (
    add_abx_row,
    add_diagnosis_row,
    add_intervention_row,
    add_ismp_row,
    delete_table_row,
)
from app.ui.emz.form_table_appliers import (
    apply_abx_rows,
    apply_diagnosis_rows,
    apply_intervention_rows,
    apply_ismp_rows,
)
from app.ui.emz.form_table_collectors import (
    collect_abx,
    collect_diagnoses,
    collect_interventions,
    collect_ismp,
)
from app.ui.emz.form_ui_state_orchestrators import (
    apply_form_read_only_state,
    apply_patient_read_only_state,
    notify_case_selection,
    reset_full_form_fields,
    reset_hospitalization_fields,
    set_quick_action_buttons_visible,
)
from app.ui.emz.form_utils import (
    parse_datetime_text,
    sex_code_to_label,
)
from app.ui.emz.form_validators import (
    validate_required_fields,
    validate_table_datetime_rows,
)
from app.ui.emz.form_widget_factories import (
    create_abx_combo,
    create_date_cell,
    create_datetime_cell,
    create_diag_type_combo,
    create_icd_combo,
    create_intervention_type_combo,
    create_ismp_type_combo,
)
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import clear_status, set_status, show_error
from app.ui.widgets.responsive_actions import ResponsiveActionsPanel
from app.ui.widgets.table_utils import (
    connect_combo_autowidth,
    connect_combo_resize_on_first_row,
    resize_columns_by_first_row,
)


class IntColumnDelegate(QStyledItemDelegate):
    def __init__(self, min_value: int = 0, max_value: int = 100000, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._min_value = min_value
        self._max_value = max_value

    def createEditor(self, parent: QWidget, option, index):  # type: ignore[override]  # noqa: N802
        editor = QLineEdit(parent)
        editor.setValidator(QIntValidator(self._min_value, self._max_value, editor))
        return editor

    def setEditorData(self, editor: QWidget, index) -> None:  # type: ignore[override]  # noqa: N802
        if isinstance(editor, QLineEdit):
            value = index.data(Qt.ItemDataRole.EditRole)
            editor.setText("" if value is None else str(value))

    def setModelData(self, editor: QWidget, model, index) -> None:  # type: ignore[override]  # noqa: N802
        if isinstance(editor, QLineEdit):
            model.setData(index, editor.text().strip(), Qt.ItemDataRole.EditRole)


class EmzForm(QWidget):
    def __init__(
        self,
        container: Container,
        on_case_selected: Callable[[int | None, int | None], None] | None = None,
        on_edit_patient: Callable[[int], None] | None = None,
        on_data_changed: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.container = container
        self.on_case_selected = on_case_selected
        self.on_edit_patient = on_edit_patient
        self.on_data_changed = on_data_changed
        self._edit_mode = False
        self.emr_case_id: int | None = None
        self._current_patient_id: int | None = None
        self._icd_list: list[Any] = []
        self._abx_list: list[Any] = []
        self._ismp_abbrev_list: list[Any] = []
        self._icd_search_updating = False
        self._date_empty = QDate(2024, 1, 1)
        self._dt_empty = QDateTime(QDate(2024, 1, 1), QTime(0, 0))
        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)
        self._build_title_row(main_layout)
        self._build_quick_actions_row(main_layout)
        self._build_patient_hint_row(main_layout)
        self._build_form_box()
        self._build_table_boxes()
        self._build_status_label()
        main_layout.addWidget(self._build_scroll_area())
        self._initialize_table_rows()

    def _build_title_row(self, main_layout: QVBoxLayout) -> None:
        title_row = QHBoxLayout()
        title = QLabel("ЭМЗ")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        main_layout.addLayout(title_row)

    def _build_quick_actions_row(self, main_layout: QVBoxLayout) -> None:
        self.quick_new_btn = QPushButton("Новая госпитализация")
        compact_button(self.quick_new_btn, min_width=96, max_width=180)
        self.quick_new_btn.clicked.connect(self._start_new_case)
        self.quick_last_btn = QPushButton("Открыть последнюю")
        compact_button(self.quick_last_btn, min_width=96, max_width=180)
        self.quick_last_btn.clicked.connect(self._open_last_case)
        self.quick_clear_btn = QPushButton("Очистить форму")
        compact_button(self.quick_clear_btn, min_width=96, max_width=180)
        self.quick_clear_btn.clicked.connect(self._reset_form)
        self.quick_save_btn = QPushButton("Сохранить ЭМЗ")
        self.quick_save_btn.setObjectName("primaryButton")
        compact_button(self.quick_save_btn, min_width=96, max_width=180)
        self.quick_save_btn.clicked.connect(self.on_save_clicked)
        self._quick_actions_panel = ResponsiveActionsPanel(min_button_width=104, max_columns=4)
        self._quick_actions_panel.set_buttons(
            [self.quick_new_btn, self.quick_last_btn, self.quick_clear_btn, self.quick_save_btn]
        )
        self._quick_actions_panel.set_compact(self.width() < 1380)
        main_layout.addWidget(self._quick_actions_panel)

    def _build_patient_hint_row(self, main_layout: QVBoxLayout) -> None:
        patient_hint_row = QHBoxLayout()
        self.patient_hint = QLabel("Создание ЭМЗ: заполните данные пациента и госпитализации.")
        self.patient_hint.setObjectName("muted")
        patient_hint_row.addWidget(self.patient_hint)
        patient_hint_row.addStretch()
        self.edit_patient_btn = QPushButton("Редактировать пациента")
        compact_button(self.edit_patient_btn)
        self.edit_patient_btn.clicked.connect(self._open_patient_edit)
        self.edit_patient_btn.setEnabled(False)
        self.edit_patient_btn.setVisible(False)
        patient_hint_row.addWidget(self.edit_patient_btn)
        main_layout.addLayout(patient_hint_row)

    def _build_form_box(self) -> None:
        self.form_box = QGroupBox("Пациент и госпитализация", self)
        form_layout = QGridLayout()
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(10)

        self._init_form_widgets()

        form_layout.addWidget(QLabel("ФИО *"), 0, 0)
        form_layout.addWidget(self.full_name, 0, 1)
        form_layout.addWidget(QLabel("Дата рождения"), 1, 0)
        form_layout.addWidget(self.dob, 1, 1)
        form_layout.addWidget(QLabel("Пол (М/Ж)"), 2, 0)
        form_layout.addWidget(self.sex, 2, 1)
        form_layout.addWidget(QLabel("Категория военнослужащего *"), 3, 0)
        form_layout.addWidget(self.category_combo, 3, 1)
        form_layout.addWidget(QLabel("Воинская часть"), 4, 0)
        form_layout.addWidget(self.military_unit, 4, 1)
        form_layout.addWidget(QLabel("Военный округ"), 5, 0)
        form_layout.addWidget(self.military_district, 5, 1)
        form_layout.addWidget(QLabel("№ истории болезни *"), 6, 0)
        form_layout.addWidget(self.hospital_case_no, 6, 1)
        form_layout.addWidget(QLabel("Отделение *"), 7, 0)
        form_layout.addWidget(self.department_combo, 7, 1)
        form_layout.addWidget(QLabel("Дата/время травмы"), 0, 2)
        form_layout.addWidget(self.injury_date, 0, 3)
        form_layout.addWidget(QLabel("Дата/время поступления"), 1, 2)
        form_layout.addWidget(self.admission_date, 1, 3)
        form_layout.addWidget(QLabel("Дата/время исхода"), 2, 2)
        form_layout.addWidget(self.outcome_date, 2, 3)
        form_layout.addWidget(QLabel("Тяжесть"), 3, 2)
        form_layout.addWidget(self.severity, 3, 3)
        form_layout.addWidget(QLabel("SOFA"), 4, 2)
        form_layout.addWidget(self.sofa_score, 4, 3)
        form_layout.addWidget(QLabel("ВПХ-П"), 5, 2)
        form_layout.addWidget(self.vph_p_score, 5, 3)
        self.form_box.setLayout(form_layout)

    def _init_form_widgets(self) -> None:
        self.full_name = QLineEdit()
        self.full_name.setToolTip("ФИО пациента. Обязательное поле.")
        self.dob = QDateEdit()
        self.dob.setCalendarPopup(True)
        self.dob.setDisplayFormat("dd.MM.yyyy")
        self.dob.setToolTip("Дата рождения: ДД.ММ.ГГГГ.")
        self.sex = QComboBox()
        self.sex.addItems(["М", "Ж"])
        connect_combo_autowidth(self.sex)
        self.category_combo = QComboBox()
        self.category_combo.addItem("Выбрать", None)
        for value in MilitaryCategory.values():
            self.category_combo.addItem(value, value)
        connect_combo_autowidth(self.category_combo)
        self.military_unit = QLineEdit()
        self.military_unit.setToolTip("Воинская часть (если применимо).")
        self.military_district = QLineEdit()
        self.military_district.setToolTip("Военный округ (если применимо).")
        self.hospital_case_no = QLineEdit()
        self.hospital_case_no.setToolTip("Номер истории болезни. Обязательное поле.")
        self.department_combo = QComboBox()
        self.department_combo.setEditable(False)
        self.department_combo.addItem("Выбрать", None)

        self.injury_date = QDateTimeEdit(calendarPopup=True)
        self.injury_date.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.admission_date = QDateTimeEdit(calendarPopup=True)
        self.admission_date.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.outcome_date = QDateTimeEdit(calendarPopup=True)
        self.outcome_date.setDisplayFormat("dd.MM.yyyy HH:mm")
        min_dt = self._dt_empty
        self.injury_date.setMinimumDateTime(min_dt)
        self.admission_date.setMinimumDateTime(min_dt)
        self.outcome_date.setMinimumDateTime(min_dt)
        self.injury_date.setSpecialValueText("")
        self.admission_date.setSpecialValueText("")
        self.outcome_date.setSpecialValueText("")
        self.injury_date.setDateTime(self._dt_empty)
        self.admission_date.setDateTime(self._dt_empty)
        self.outcome_date.setDateTime(self._dt_empty)
        self.injury_date.setToolTip("Дата/время травмы: ДД.ММ.ГГГГ ЧЧ:ММ.")
        self.admission_date.setToolTip("Дата/время поступления: ДД.ММ.ГГГГ ЧЧ:ММ.")
        self.outcome_date.setToolTip("Дата/время исхода: ДД.ММ.ГГГГ ЧЧ:ММ.")
        self.severity = QLineEdit()
        self.sofa_score = QLineEdit()
        self.vph_p_score = QLineEdit()
        self.sofa_score.setValidator(QIntValidator(0, 1000, self))
        self.vph_p_score.setValidator(QIntValidator(0, 1000, self))
        self.sofa_score.setToolTip("SOFA: только целое число.")
        self.vph_p_score.setToolTip("ВПХ-П: балльная оценка тяжести повреждений.")

    def _build_table_boxes(self) -> None:
        self._build_tables()
        self.diag_box = self._build_collapsible_table_box("Диагнозы", self.diagnosis_table, self._add_diagnosis_row)
        self.interv_box = self._build_collapsible_table_box(
            "Интервенции",
            self.intervention_table,
            self._add_intervention_row,
        )
        self.abx_box = self._build_collapsible_table_box("Антибиотики", self.abx_table, self._add_abx_row)
        self.ismp_box = self._build_collapsible_table_box("ИСМП", self.ismp_table, self._add_ismp_row)

    def _build_tables(self) -> None:
        self.diagnosis_table = self._make_table(["Тип", "МКБ-10", "Текст"], 1)
        self.diagnosis_table.setProperty("min_column_widths", {0: 150})
        self.diagnosis_table.setMinimumHeight(170)
        self._set_table_tooltip(self.diagnosis_table, 0, "Тип диагноза: поступление/перевод/выписка/осложнение.")
        self._set_table_tooltip(self.diagnosis_table, 1, "Код МКБ-10 из списка.")
        self._set_table_tooltip(self.diagnosis_table, 2, "Свободный текст диагноза (если нет кода).")

        self.intervention_table = self._make_table(
            [
                "Тип",
                "Начало (ДД.ММ.ГГГГ ЧЧ:ММ)",
                "Окончание (ДД.ММ.ГГГГ ЧЧ:ММ)",
                "Длительность (мин)",
                "Кем выполнено",
                "Примечания",
            ],
            1,
        )
        self.intervention_table.setItemDelegateForColumn(3, IntColumnDelegate(0, 100000, self.intervention_table))
        self.intervention_table.setMinimumHeight(190)
        self._set_table_tooltip(self.intervention_table, 1, "Дата/время начала: 31.12.2025 10:00")
        self._set_table_tooltip(self.intervention_table, 2, "Дата/время окончания: 31.12.2025 12:00")
        self._set_table_tooltip(self.intervention_table, 3, "Длительность в минутах (если известно).")

        self.abx_table = self._make_table(
            [
                "Начало (ДД.ММ.ГГГГ ЧЧ:ММ)",
                "Окончание (ДД.ММ.ГГГГ ЧЧ:ММ)",
                "Антибиотик",
                "Свободное имя",
                "Путь введения",
            ],
            1,
        )
        self.abx_table.setMinimumHeight(170)
        self._set_table_tooltip(self.abx_table, 0, "Дата/время начала: 31.12.2025 10:00")
        self._set_table_tooltip(self.abx_table, 1, "Дата/время окончания: 31.12.2025 12:00")
        self._set_table_tooltip(self.abx_table, 2, "Выберите антибиотик из списка.")
        self._set_table_tooltip(self.abx_table, 3, "Свободное имя препарата (если нет в списке).")

        self.ismp_table = self._make_table(["Тип ИСМП", "Дата начала"], 1)
        self.ismp_table.setMinimumHeight(140)
        self._set_table_tooltip(self.ismp_table, 0, "Тип ИСМП (ВАП, КА-ИК, КА-ИМП).")
        self._set_table_tooltip(self.ismp_table, 1, "Дата начала: ДД.ММ.ГГГГ.")

    def _build_collapsible_table_box(
        self,
        title: str,
        table: QTableWidget,
        add_callback: Callable[[], None],
    ) -> QGroupBox:
        box = QGroupBox(title)
        layout = QVBoxLayout()
        controls = QHBoxLayout()
        add_btn = QPushButton("Добавить строку")
        compact_button(add_btn)
        add_btn.clicked.connect(add_callback)
        del_btn = QPushButton("Удалить строку")
        compact_button(del_btn)
        del_btn.clicked.connect(lambda: self._delete_table_row(table))
        controls.addWidget(add_btn)
        controls.addWidget(del_btn)
        controls.addStretch()

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(table)
        content_layout.addLayout(controls)
        layout.addWidget(content)

        box.setLayout(layout)
        box.setCheckable(True)
        box.setChecked(True)
        box.toggled.connect(content.setVisible)
        return box

    def _build_status_label(self) -> None:
        self.status_label = QLabel()
        set_status(self.status_label, "", "info")

    def _build_scroll_area(self) -> QScrollArea:
        wrapper = QWidget()
        wrapper.setLayout(self._build_content_layout())
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(wrapper)
        return scroll

    def _build_content_layout(self) -> QVBoxLayout:
        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)
        required_label = QLabel("Обязательные поля отмечены *.")
        required_label.setObjectName("muted")
        content_layout.addWidget(required_label)
        content_layout.addWidget(self.form_box)
        content_layout.addWidget(self.diag_box)
        content_layout.addWidget(self.interv_box)
        content_layout.addWidget(self.abx_box)
        content_layout.addWidget(self.ismp_box)
        content_layout.addLayout(self._build_footer_row())
        content_layout.addStretch()
        return content_layout

    def _build_footer_row(self) -> QHBoxLayout:
        footer_row = QHBoxLayout()
        footer_row.addWidget(self.status_label)
        footer_row.addStretch()
        return footer_row

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_quick_actions_panel"):
            self._quick_actions_panel.set_compact(self.width() < 1380)

    def _initialize_table_rows(self) -> None:
        self._load_references()
        self._setup_all_detail_tables()

    def _date_value(self, widget: QDateEdit) -> date | None:
        if not widget.date().isValid():
            return None
        return cast(date, widget.date().toPython())

    def _datetime_value(self, widget: QDateTimeEdit) -> datetime | None:
        if not widget.dateTime().isValid():
            return None
        qdt = widget.dateTime()
        if qdt == self._dt_empty:
            return None
        return cast(datetime, qdt.toPython())

    def _to_qdate(self, value: date) -> QDate:
        return QDate(value.year, value.month, value.day)

    def _to_qdatetime(self, value: datetime) -> QDateTime:
        return QDateTime(
            self._to_qdate(value.date()),
            QTime(value.hour, value.minute, value.second),
        )

    def _create_dt_cell(self) -> QDateTimeEdit:
        return create_datetime_cell(self._dt_empty)

    def _dt_from_cell(self, widget: QDateTimeEdit | None) -> datetime | None:
        if widget is None:
            return None
        qdt = widget.dateTime()
        if qdt == self._dt_empty:
            return None
        return cast(datetime, qdt.toPython())

    def _table_dt_value(self, table: QTableWidget, row: int, col: int) -> datetime | None:
        dt_widget = table.cellWidget(row, col)
        dt_value = self._dt_from_cell(cast(QDateTimeEdit, dt_widget) if isinstance(dt_widget, QDateTimeEdit) else None)
        if dt_value is not None:
            return dt_value
        item = table.item(row, col)
        return self._parse_dt(item.text() if item else None)

    def _set_table_tooltip(self, table: QTableWidget, col: int, text: str) -> None:
        item = table.horizontalHeaderItem(col)
        if item is not None:
            item.setToolTip(text)

    def _make_table(self, headers: list[str], rows: int) -> QTableWidget:
        table = QTableWidget(rows, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.SelectedClicked
            | QTableWidget.EditTrigger.EditKeyPressed
        )
        table.itemChanged.connect(self._on_first_row_changed)
        resize_columns_by_first_row(table)
        return table

    def _resize_table_columns(self, table: QTableWidget) -> None:
        # Keep a double-pass resize for stable widths with mixed editors/widgets.
        resize_columns_by_first_row(table)
        resize_columns_by_first_row(table)

    def _prepare_table_for_fill(self, table: QTableWidget, item_count: int) -> None:
        table.clearContents()
        table.setRowCount(max(item_count, table.rowCount()))

    def _setup_all_detail_tables(self) -> None:
        self._icd_list = self.container.reference_service.list_icd10()
        self._abx_list = self.container.reference_service.list_antibiotics()
        self._ismp_abbrev_list = self.container.reference_service.list_ismp_abbreviations()
        setup_detail_reference_rows(
            diagnosis_table=self.diagnosis_table,
            intervention_table=self.intervention_table,
            abx_table=self.abx_table,
            ismp_table=self.ismp_table,
            create_diag_type_combo=create_diag_type_combo,
            create_icd_combo=self._create_icd_combo,
            create_intervention_type_combo=create_intervention_type_combo,
            create_dt_cell=self._create_dt_cell,
            create_abx_combo=self._create_abx_combo,
            create_ismp_type_combo=self._create_ismp_type_combo,
            create_date_cell=self._create_date_cell,
            resize_table=self._resize_table_columns,
        )

    def _reset_detail_tables(self) -> None:
        for table in (self.diagnosis_table, self.intervention_table, self.abx_table, self.ismp_table):
            table.clearContents()
            table.setRowCount(1)
        self._setup_all_detail_tables()

    def _on_first_row_changed(self, item: QTableWidgetItem) -> None:
        if item and item.row() == 0:
            table = item.tableWidget()
            if table is not None:
                self._resize_table_columns(table)

    def _load_references(self) -> None:
        try:
            apply_departments_to_combo(
                department_combo=self.department_combo,
                departments=self.container.reference_service.list_departments(),
                connect_combo_autowidth=connect_combo_autowidth,
            )
        except ValueError as exc:
            self._set_status(str(exc), "warning")
            show_error(self, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Не удалось загрузить справочник отделений: {exc}", "error")

    def refresh_references(self) -> None:
        current_department = self.department_combo.currentData()
        self._load_references()
        restore_department_selection(
            department_combo=self.department_combo,
            current_department=current_department,
        )
        self._icd_list = self.container.reference_service.list_icd10()
        self._abx_list = self.container.reference_service.list_antibiotics()
        self._ismp_abbrev_list = self.container.reference_service.list_ismp_abbreviations()
        refresh_detail_reference_rows(
            diagnosis_table=self.diagnosis_table,
            abx_table=self.abx_table,
            ismp_table=self.ismp_table,
            create_diag_type_combo=create_diag_type_combo,
            create_icd_combo=self._create_icd_combo,
            create_abx_combo=self._create_abx_combo,
            create_ismp_type_combo=self._create_ismp_type_combo,
            resize_table=self._resize_table_columns,
        )

    def _create_icd_combo(self) -> QComboBox:
        return create_icd_combo(icd_items=self._icd_list, wire_search=self._wire_icd_search)

    def _wire_icd_search(self, combo: QComboBox) -> None:
        def _on_text(text: str) -> None:
            if self._icd_search_updating:
                return
            self._icd_search_updating = True
            try:
                self._refresh_icd_combo(combo, text)
            finally:
                self._icd_search_updating = False

        wire_icd_search(combo, _on_text)

    def _refresh_icd_combo(self, combo: QComboBox, text: str) -> None:
        refresh_icd_combo(
            combo=combo,
            text=text,
            default_icd_items=self._icd_list,
            search_icd_items=lambda query: self.container.reference_service.search_icd10(query, limit=50),
        )

    def _create_abx_combo(self) -> QComboBox:
        return create_abx_combo(antibiotics=self._abx_list)

    def _create_ismp_type_combo(self) -> QComboBox:
        if not self._ismp_abbrev_list:
            self._ismp_abbrev_list = self.container.reference_service.list_ismp_abbreviations()
        return create_ismp_type_combo(
            abbreviations=self._ismp_abbrev_list,
            tooltip_role=int(Qt.ItemDataRole.ToolTipRole),
        )

    def _create_date_cell(self) -> QDateEdit:
        return create_date_cell(self._date_empty)

    def _add_diagnosis_row(self) -> None:
        add_diagnosis_row(
            table=self.diagnosis_table,
            create_type_combo=create_diag_type_combo,
            create_icd_combo=self._create_icd_combo,
            connect_combo_resize=connect_combo_resize_on_first_row,
        )

    def _add_intervention_row(self) -> None:
        add_intervention_row(
            table=self.intervention_table,
            create_type_combo=create_intervention_type_combo,
            create_dt_cell=self._create_dt_cell,
            connect_combo_resize=connect_combo_resize_on_first_row,
        )

    def _add_abx_row(self) -> None:
        add_abx_row(
            table=self.abx_table,
            create_dt_cell=self._create_dt_cell,
            create_abx_combo=self._create_abx_combo,
            connect_combo_resize=connect_combo_resize_on_first_row,
        )

    def _add_ismp_row(self) -> None:
        add_ismp_row(
            table=self.ismp_table,
            create_type_combo=self._create_ismp_type_combo,
            create_date_cell=self._create_date_cell,
            connect_combo_resize=connect_combo_resize_on_first_row,
        )

    def _delete_table_row(self, table: QTableWidget) -> None:
        delete_table_row(table)

    def _parse_dt(self, text: str | None) -> datetime | None:
        return parse_datetime_text(text)

    def _set_patient_identity_fields(
        self,
        *,
        full_name: str,
        dob: date | None,
        sex_code: str | None,
        category: str | None,
        military_unit: str | None,
        military_district: str | None,
    ) -> None:
        self.full_name.setText(full_name)
        if dob:
            self.dob.setDate(self._to_qdate(dob))
        self.sex.setCurrentText(sex_code_to_label(sex_code))
        idx_cat = self.category_combo.findData(category)
        if idx_cat >= 0:
            self.category_combo.setCurrentIndex(idx_cat)
        self.military_unit.setText(military_unit or "")
        self.military_district.setText(military_district or "")

    def _apply_patient_identity_data(self, identity: PatientIdentityData) -> None:
        self._set_patient_identity_fields(
            full_name=identity.full_name,
            dob=identity.dob,
            sex_code=identity.sex_code,
            category=identity.category,
            military_unit=identity.military_unit,
            military_district=identity.military_district,
        )

    def _collect_diagnoses(self) -> list[EmzDiagnosisDto]:
        return collect_diagnoses(table=self.diagnosis_table)

    def _collect_interventions(self) -> list[EmzInterventionDto]:
        return collect_interventions(
            table=self.intervention_table,
            dt_resolver=self._table_dt_value,
        )

    def _collect_abx(self) -> list[EmzAntibioticCourseDto]:
        return collect_abx(
            table=self.abx_table,
            dt_resolver=self._table_dt_value,
        )

    def _collect_ismp(self) -> list[EmzIsmpDto]:
        return collect_ismp(
            table=self.ismp_table,
            date_empty=self._date_empty,
        )

    def _validate_required(self) -> bool:
        message = validate_required_fields(
            full_name=self.full_name.text(),
            hospital_case_no=self.hospital_case_no.text(),
            category_value=self.category_combo.currentData(),
        )
        if message:
            self._set_status(message, "warning")
            return False
        return True

    def _validate_tables_dt(self) -> bool:
        table_specs = (
            (self.intervention_table, (1, 2), ((1, 2),)),
            (self.abx_table, (0, 1), ((0, 1),)),
        )
        for table, datetime_cols, range_pairs in table_specs:
            error = validate_table_datetime_rows(
                table=table,
                datetime_cols=datetime_cols,
                range_pairs=range_pairs,
                dt_resolver=self._table_dt_value,
            )
            if error:
                self._set_status(error, "error")
                return False
        return True

    def _parse_int(self, text: str | None, field_label: str) -> int | None:
        return parse_optional_int(text, field_label)

    def _text_or_none(self, field: QLineEdit) -> str | None:
        value = field.text().strip()
        return value or None

    def _normalize_sex(self) -> str:
        return normalize_sex_label(self.sex.currentText())

    def _format_save_message(self) -> str:
        return format_save_message(
            patient_name=self.full_name.text(),
            hospital_case_no=self.hospital_case_no.text(),
            admission_value=self._datetime_value(self.admission_date),
        )

    def _resolve_department_id(self) -> int | None:
        return resolve_department_id(
            selected_id=cast(int | None, self.department_combo.currentData()),
            selected_name=self.department_combo.currentText(),
            departments=self.container.reference_service.list_departments(),
        )

    def _set_patient_read_only(self, read_only: bool) -> None:
        self._patient_read_only = read_only
        apply_patient_read_only_state(
            read_only=read_only,
            edit_mode=self._edit_mode,
            has_current_patient=self._current_patient_id is not None,
            full_name=self.full_name,
            dob=self.dob,
            sex=self.sex,
            category_combo=self.category_combo,
            military_unit=self.military_unit,
            military_district=self.military_district,
            edit_patient_btn=self.edit_patient_btn,
            patient_hint=self.patient_hint,
            build_patient_hint=lambda read_only, edit_mode: patient_hint_for_read_only(
                read_only=read_only,
                edit_mode=edit_mode,
            ),
        )

    def _set_form_read_only(self, read_only: bool) -> None:
        apply_form_read_only_state(
            read_only=read_only,
            sections=(self.form_box, self.diag_box, self.interv_box, self.abx_box, self.ismp_box),
            quick_save_btn=self.quick_save_btn,
        )

    def set_edit_mode(self, enabled: bool) -> None:
        self._edit_mode = enabled
        state = build_edit_mode_ui_state(enabled)
        self._set_form_read_only(state.form_read_only)
        self._set_patient_read_only(state.patient_read_only)
        if state.patient_hint:
            self.patient_hint.setText(state.patient_hint)
        self.quick_save_btn.setText(state.quick_save_text)
        self.edit_patient_btn.setVisible(False)
        set_quick_action_buttons_visible(
            visible=state.show_quick_actions,
            quick_new_btn=self.quick_new_btn,
            quick_last_btn=self.quick_last_btn,
            quick_clear_btn=self.quick_clear_btn,
        )

    def _reset_form(self, *, emit_context: bool = True) -> None:
        self.emr_case_id = None
        self._current_patient_id = None
        self._edit_mode = False
        self.quick_save_btn.setText("Сохранить ЭМЗ")
        reset_full_form_fields(
            full_name=self.full_name,
            dob=self.dob,
            sex=self.sex,
            category_combo=self.category_combo,
            military_unit=self.military_unit,
            military_district=self.military_district,
            hospital_case_no=self.hospital_case_no,
            department_combo=self.department_combo,
            injury_date=self.injury_date,
            admission_date=self.admission_date,
            outcome_date=self.outcome_date,
            severity=self.severity,
            sofa_score=self.sofa_score,
            vph_p_score=self.vph_p_score,
            default_date=QDate.currentDate(),
            default_datetime=QDateTime.currentDateTime(),
            reset_detail_tables=self._reset_detail_tables,
        )
        self._set_patient_read_only(False)
        self._set_form_read_only(False)
        notify_case_selection(
            callback=self.on_case_selected,
            patient_id=None,
            emr_case_id=None,
            emit=emit_context,
        )

    def clear_context(self) -> None:
        clear_status(self.status_label)
        self._reset_form(emit_context=False)

    def _start_new_case(self) -> None:
        if not self._current_patient_id:
            self._reset_form()
            self._set_status("Заполните данные пациента для новой госпитализации.", "info")
            return
        # Keep patient info, reset hospitalization-specific fields.
        self.emr_case_id = None
        reset_hospitalization_fields(
            hospital_case_no=self.hospital_case_no,
            department_combo=self.department_combo,
            injury_date=self.injury_date,
            admission_date=self.admission_date,
            outcome_date=self.outcome_date,
            severity=self.severity,
            sofa_score=self.sofa_score,
            vph_p_score=self.vph_p_score,
            empty_datetime=self._dt_empty,
            reset_detail_tables=self._reset_detail_tables,
        )
        patient_read_only, form_read_only, patient_hint = build_new_case_access_state(self._edit_mode)
        self._set_patient_read_only(patient_read_only)
        self._set_form_read_only(form_read_only)
        if patient_hint:
            self.patient_hint.setText(patient_hint)
        notify_case_selection(
            callback=self.on_case_selected,
            patient_id=self._current_patient_id,
            emr_case_id=None,
        )
        self._set_status("Новая госпитализация: заполните данные.", "info")

    def _open_last_case(self) -> None:
        if not self._current_patient_id:
            self._set_status("Сначала выберите пациента.", "warning")
            return
        try:
            cases = self.container.emz_service.list_cases_by_patient(self._current_patient_id)
            if not cases:
                self._set_status("Нет госпитализаций для выбранного пациента.", "info")
                return
            case_dates: list[tuple[int, datetime | None, datetime | None]] = []
            for case in cases:
                detail = self.container.emz_service.get_current(case.id)
                case_dates.append((case.id, detail.admission_date, detail.outcome_date))
            latest_id = pick_latest_case_id(case_dates)
            if latest_id is None:
                self._set_status("Не удалось определить последнюю госпитализацию.", "warning")
                return
            self.load_case(self._current_patient_id, latest_id)
        except ValueError as exc:
            self._set_status(str(exc), "warning")
            show_error(self, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Не удалось открыть последнюю госпитализацию: {exc}", "error")

    def _build_payload(self) -> EmzVersionPayload:
        return build_emz_version_payload(
            admission_date=self._datetime_value(self.admission_date),
            injury_date=self._datetime_value(self.injury_date),
            outcome_date=self._datetime_value(self.outcome_date),
            severity=self.severity.text() or None,
            sofa_score=self._parse_int(self.sofa_score.text(), "SOFA"),
            vph_p_or_score=self._parse_int(self.vph_p_score.text(), "ВПХ-П"),
            diagnoses=self._collect_diagnoses(),
            interventions=self._collect_interventions(),
            antibiotic_courses=self._collect_abx(),
            ismp_cases=self._collect_ismp(),
        )

    def _notify_case_changed(self, patient_id: int | None, emr_case_id: int | None) -> None:
        if self.on_case_selected:
            self.on_case_selected(patient_id, emr_case_id)
        if self.on_data_changed:
            self.on_data_changed()

    def _save_new_case(self, payload: EmzVersionPayload, category_value: str, department_value: int | None) -> None:
        create_req = build_emz_create_request(
            patient_full_name=self.full_name.text(),
            patient_dob=self._date_value(self.dob),
            patient_sex=self._normalize_sex(),
            patient_category=category_value,
            patient_military_unit=self._text_or_none(self.military_unit),
            patient_military_district=self._text_or_none(self.military_district),
            hospital_case_no=self.hospital_case_no.text(),
            department_id=department_value,
            payload=payload,
        )
        resp = self.container.emz_service.create_emr(create_req, actor_id=None)
        self.emr_case_id = resp.id
        detail = self.container.emz_service.get_current(resp.id)
        self._current_patient_id = detail.patient_id
        self._set_patient_read_only(True)
        self._set_form_read_only(False)
        self._set_status(self._format_save_message(), "success")
        self._notify_case_changed(detail.patient_id, resp.id)

    def _save_existing_case(self, payload: EmzVersionPayload, category_value: str, department_value: int | None) -> None:
        if self.emr_case_id is None:
            raise ValueError("Не выбрана госпитализация для обновления")
        emr_case_id = self.emr_case_id
        if self._current_patient_id is not None:
            patient_update = build_patient_update_fields(
                full_name=self.full_name.text().strip(),
                dob=self._date_value(self.dob),
                sex=self._normalize_sex(),
                category=category_value,
                military_unit=self._text_or_none(self.military_unit),
                military_district=self._text_or_none(self.military_district),
            )
            self.container.patient_service.update_details(
                self._current_patient_id,
                full_name=patient_update.full_name,
                dob=patient_update.dob,
                sex=patient_update.sex,
                category=patient_update.category,
                military_unit=patient_update.military_unit,
                military_district=patient_update.military_district,
            )
        self.container.emz_service.update_case_meta(
            emr_case_id,
            hospital_case_no=self.hospital_case_no.text(),
            department_id=department_value,
            actor_id=None,
        )
        update_req = build_emz_update_request(emr_case_id=emr_case_id, payload=payload)
        self.container.emz_service.update_emr(update_req, actor_id=None)
        self._set_status(self._format_save_message(), "success")
        self._notify_case_changed(self._current_patient_id, emr_case_id)

    def on_save_clicked(self) -> None:
        clear_status(self.status_label)
        try:
            context = collect_save_case_context(
                validate_required=self._validate_required,
                validate_tables_dt=self._validate_tables_dt,
                build_payload=self._build_payload,
                get_category_value=lambda: cast(str, self.category_combo.currentData()),
                get_department_value=self._resolve_department_id,
                emr_case_id=self.emr_case_id,
            )
            if context is None:
                return
            run_save_case(
                context=context,
                save_new=self._save_new_case,
                save_existing=self._save_existing_case,
            )
        except ValueError as exc:
            self._set_status(str(exc), "warning")
            show_error(self, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Ошибка: {exc}", "error")
            show_error(self, str(exc))

    def _apply_case_access_state(self) -> None:
        if self._edit_mode:
            self._set_patient_read_only(False)
            self._set_form_read_only(False)
        else:
            self._set_patient_read_only(True)
            self._set_form_read_only(True)

    def _set_datetime_field_from_case_value(self, widget: QDateTimeEdit, value: date | datetime | None) -> None:
        dt_value, date_value = split_date_or_datetime(value)
        if dt_value is not None:
            widget.setDateTime(self._to_qdatetime(dt_value))
            return
        if date_value is not None:
            widget.setDate(self._to_qdate(date_value))
            return
        widget.setDateTime(self._dt_empty)

    def _apply_case_header_fields(self, detail: EmzCaseDetail) -> None:
        self.hospital_case_no.setText(detail.hospital_case_no)
        idx = self.department_combo.findData(detail.department_id)
        if idx >= 0:
            self.department_combo.setCurrentIndex(idx)
        self._set_datetime_field_from_case_value(self.admission_date, detail.admission_date)
        self._set_datetime_field_from_case_value(self.injury_date, detail.injury_date)
        self._set_datetime_field_from_case_value(self.outcome_date, detail.outcome_date)
        self.severity.setText(text_or_empty(detail.severity))
        self.sofa_score.setText(int_or_empty(detail.sofa_score))
        self.vph_p_score.setText(int_or_empty(detail.vph_p_or_score))

    def _apply_patient_selection_for_new_case(
        self,
        *,
        patient_id: int,
        identity: PatientIdentityData,
        emit_context: bool,
    ) -> None:
        self._current_patient_id = patient_id
        self._apply_patient_identity_data(identity)
        self._set_patient_read_only(True)
        self._set_form_read_only(False)
        self.patient_hint.setText(
            "Новая госпитализация: заполните данные. "
            "Редактирование данных пациента — кнопкой «Редактировать пациента»."
        )
        self._set_status(f"Пациент выбран: {identity.full_name}. Выберите госпитализацию.", "info")
        if emit_context and self.on_case_selected:
            self.on_case_selected(patient_id, None)

    def _apply_detail(self, detail: EmzCaseDetail, *, emit_context: bool = True) -> None:
        self.emr_case_id = detail.id
        self._current_patient_id = detail.patient_id
        self._apply_case_access_state()
        if emit_context and self.on_case_selected:
            self.on_case_selected(detail.patient_id, detail.id)
        self._apply_patient_identity_data(identity_from_case_detail(detail))
        self._apply_case_header_fields(detail)
        self._fill_table_from_dto(self.diagnosis_table, detail.diagnoses)
        self._fill_interventions(detail.interventions)
        self._fill_abx(detail.antibiotic_courses)
        self._fill_ismp(detail.ismp_cases)

    def _set_status(self, message: str, level: str = "info") -> None:
        set_status(self.status_label, message, level)

    def refresh_patient(self, patient_id: int) -> None:
        if not self._current_patient_id or self._current_patient_id != patient_id:
            return
        try:
            patient = self.container.patient_service.get_by_id(patient_id)
        except Exception:  # noqa: BLE001
            return
        self._apply_patient_identity_data(identity_from_patient_record(patient))

    def _open_patient_edit(self) -> None:
        if not self._current_patient_id:
            self._set_status("Сначала создайте или выберите пациента.", "warning")
            return
        if self.on_edit_patient:
            self.on_edit_patient(self._current_patient_id)

    def _get_patient_identity_data(self, patient_id: int) -> tuple[int, PatientIdentityData]:
        patient = self.container.patient_service.get_by_id(patient_id)
        return patient.id, identity_from_patient_record(patient)

    def load_case(self, patient_id: int | None, emr_case_id: int | None, *, emit_context: bool = True) -> None:
        clear_status(self.status_label)
        try:
            opened_case = run_load_case(
                context=LoadCaseContext(patient_id=patient_id, emr_case_id=emr_case_id),
                get_case_detail=self.container.emz_service.get_current,
                apply_case_detail=lambda detail: self._apply_detail(detail, emit_context=emit_context),
                get_patient_identity=self._get_patient_identity_data,
                apply_patient_selection=lambda resolved_patient_id, identity: self._apply_patient_selection_for_new_case(
                    patient_id=resolved_patient_id,
                    identity=identity,
                    emit_context=emit_context,
                ),
            )
            if opened_case:
                self._set_status("ЭМЗ открыта.", "success")
        except ValueError as exc:
            self._set_status(str(exc), "warning")
            show_error(self, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self._set_status(str(exc), "error")
            show_error(self, str(exc))

    def _fill_table_from_dto(self, table: QTableWidget, items: list[EmzDiagnosisDto]) -> None:
        apply_diagnosis_rows(
            table=table,
            items=items,
            prepare_table=self._prepare_table_for_fill,
            setup_rows=lambda: setup_diagnosis_reference_rows(
                diagnosis_table=self.diagnosis_table,
                create_diag_type_combo=create_diag_type_combo,
                create_icd_combo=self._create_icd_combo,
                resize_table=self._resize_table_columns,
            ),
            resize_table=self._resize_table_columns,
        )

    def _fill_interventions(self, items: list[EmzInterventionDto]) -> None:
        apply_intervention_rows(
            table=self.intervention_table,
            items=items,
            prepare_table=self._prepare_table_for_fill,
            resize_table=self._resize_table_columns,
            create_type_combo=create_intervention_type_combo,
            create_dt_cell=self._create_dt_cell,
            to_qdatetime=self._to_qdatetime,
        )

    def _fill_abx(self, items: list[EmzAntibioticCourseDto]) -> None:
        apply_abx_rows(
            table=self.abx_table,
            items=items,
            prepare_table=self._prepare_table_for_fill,
            setup_rows=lambda: setup_abx_reference_rows(
                abx_table=self.abx_table,
                create_dt_cell=self._create_dt_cell,
                create_abx_combo=self._create_abx_combo,
                resize_table=self._resize_table_columns,
            ),
            resize_table=self._resize_table_columns,
            create_dt_cell=self._create_dt_cell,
            to_qdatetime=self._to_qdatetime,
        )

    def _fill_ismp(self, items: list[EmzIsmpDto]) -> None:
        apply_ismp_rows(
            table=self.ismp_table,
            items=items,
            prepare_table=self._prepare_table_for_fill,
            setup_rows=lambda: setup_ismp_reference_rows(
                ismp_table=self.ismp_table,
                create_ismp_type_combo=self._create_ismp_type_combo,
                create_date_cell=self._create_date_cell,
                resize_table=self._resize_table_columns,
            ),
            resize_table=self._resize_table_columns,
            create_type_combo=self._create_ismp_type_combo,
            create_date_cell=self._create_date_cell,
            to_qdate=self._to_qdate,
        )
