from __future__ import annotations

import json
from datetime import date
from typing import cast

from PySide6.QtCore import QDate, QSignalBlocker, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDateEdit,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.dto.auth_dto import SessionContext
from app.application.services.analytics_service import AnalyticsService
from app.application.services.reference_service import ReferenceService
from app.application.services.reporting_service import ReportingService
from app.application.services.saved_filter_service import SavedFilterService
from app.domain.constants import MilitaryCategory
from app.ui.analytics.charts import TopMicrobesChart, TrendChart
from app.ui.analytics.report_history_helpers import (
    format_report_verification,
    report_history_column_widths,
    to_report_history_view_row,
)
from app.ui.analytics.view_utils import (
    calculate_compare_window,
    format_analytics_datetime,
    format_day_label,
    normalize_date_range,
    quick_period_bounds,
)
from app.ui.widgets.async_task import run_async
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import show_error, show_info, show_warning
from app.ui.widgets.responsive_actions import ResponsiveActionsPanel
from app.ui.widgets.table_utils import connect_combo_autowidth, resize_columns_by_first_row


class AnalyticsSearchView(QWidget):
    def __init__(
        self,
        analytics_service: AnalyticsService,
        reference_service: ReferenceService,
        saved_filter_service: SavedFilterService,
        reporting_service: ReportingService,
        session: SessionContext,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.analytics_service = analytics_service
        self.reference_service = reference_service
        self.saved_filter_service = saved_filter_service
        self.reporting_service = reporting_service
        self.session = session
        self._search_delay_ms = 250
        self._icd_search_updating = False
        self._micro_search_updating = False
        self._abx_search_updating = False
        self._material_search_updating = False
        self._icd_pending_text = ""
        self._micro_pending_text = ""
        self._abx_pending_text = ""
        self._material_pending_text = ""
        self._icd_search_timer = QTimer(self)
        self._icd_search_timer.setSingleShot(True)
        self._icd_search_timer.timeout.connect(self._trigger_icd_refresh)
        self._micro_search_timer = QTimer(self)
        self._micro_search_timer.setSingleShot(True)
        self._micro_search_timer.timeout.connect(self._trigger_micro_refresh)
        self._abx_search_timer = QTimer(self)
        self._abx_search_timer.setSingleShot(True)
        self._abx_search_timer.timeout.connect(self._trigger_abx_refresh)
        self._material_search_timer = QTimer(self)
        self._material_search_timer.setSingleShot(True)
        self._material_search_timer.timeout.connect(self._trigger_material_refresh)
        self._build_ui()

    def set_session(self, session: SessionContext) -> None:
        self.session = session

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        title = QLabel("Поиск и аналитика")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)
        self._build_filters_section(content_layout)
        self._build_saved_filters_section(content_layout)
        self._build_actions_row(content_layout)
        self._build_summary_row(content_layout)
        self._build_report_history_section(content_layout)
        content_layout.addWidget(self._build_dashboard_box())
        content_layout.addWidget(self._build_ismp_box())
        content_layout.addWidget(self._build_top_box())
        content_layout.addWidget(self._build_results_box())
        content_layout.addStretch()

        wrapper = QWidget()
        wrapper.setLayout(content_layout)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(wrapper)
        layout.addWidget(scroll)

        self._load_saved_filters()
        self._load_report_history()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_main_actions_panel"):
            self._main_actions_panel.set_compact(self.width() < 1420)
        if hasattr(self, "_history_actions_panel"):
            self._history_actions_panel.set_compact(self.width() < 1460)

    def _build_filters_section(self, content_layout: QVBoxLayout) -> None:
        self.filters_box = QGroupBox("Параметры поиска")
        filters_layout = QVBoxLayout(self.filters_box)
        filters_layout.setSpacing(10)
        filters_layout.addLayout(self._build_quick_period_row())
        filters_layout.addLayout(self._build_filters_grid())
        content_layout.addWidget(self.filters_box)

    def _build_quick_period_row(self) -> QHBoxLayout:
        quick_row = QHBoxLayout()
        self.quick_period = QComboBox()
        self.quick_period.addItem("Сегодня", "today")
        self.quick_period.addItem("Последние 7 дней", "7d")
        self.quick_period.addItem("Последние 30 дней", "30d")
        self.quick_period.addItem("Последние 90 дней", "90d")
        self.quick_period.addItem("Текущий месяц", "month")
        connect_combo_autowidth(self.quick_period)
        quick_apply_btn = QPushButton("Применить период")
        compact_button(quick_apply_btn)
        quick_apply_btn.clicked.connect(self._apply_quick_period)
        reset_filters_btn = QPushButton("Сбросить фильтры")
        compact_button(reset_filters_btn)
        reset_filters_btn.clicked.connect(self._reset_search_filters)
        quick_row.addWidget(QLabel("Быстрый период"))
        quick_row.addWidget(self.quick_period)
        quick_row.addWidget(quick_apply_btn)
        quick_row.addStretch()
        quick_row.addWidget(reset_filters_btn)
        return quick_row

    def _build_filters_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        self._init_filter_widgets()

        grid.addWidget(QLabel("Дата от"), 0, 0)
        grid.addWidget(self.date_from, 0, 1)
        grid.addWidget(QLabel("Дата по"), 0, 2)
        grid.addWidget(self.date_to, 0, 3)
        grid.addWidget(QLabel("Отделение"), 1, 0)
        grid.addWidget(self.department, 1, 1)
        grid.addWidget(QLabel("МКБ-10"), 1, 2)
        grid.addWidget(self.icd10, 1, 3)
        grid.addWidget(QLabel("Микроорганизм"), 2, 0)
        grid.addWidget(self.microbe, 2, 1)
        grid.addWidget(QLabel("Антибиотик"), 2, 2)
        grid.addWidget(self.antibiotic, 2, 3)
        grid.addWidget(QLabel("Материал"), 3, 0)
        grid.addWidget(self.material, 3, 1)
        grid.addWidget(QLabel("Рост"), 3, 2)
        grid.addWidget(self.growth_flag, 3, 3)
        grid.addWidget(QLabel("Категория"), 4, 0)
        grid.addWidget(self.patient_category, 4, 1)
        grid.addWidget(QLabel("Пациент (ФИО)"), 4, 2)
        grid.addWidget(self.patient_name, 4, 3)
        grid.addWidget(QLabel("Номер пробы"), 5, 0)
        grid.addWidget(self.lab_no, 5, 1)
        grid.addWidget(QLabel("Полнотекстовый поиск"), 6, 0)
        grid.addWidget(self.search_text, 6, 1, 1, 3)
        return grid

    def _init_filter_widgets(self) -> None:
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setMinimumDate(QDate(2024, 1, 1))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setMinimumDate(QDate(2024, 1, 1))
        self.department = QComboBox()
        self.department.addItem("Выбрать", None)
        for dep in self.reference_service.list_departments():
            self.department.addItem(str(dep.name), cast(int, dep.id))
        self.icd10 = QComboBox()
        self.icd10.setEditable(True)
        self.icd10.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.icd10.addItem("Выбрать", None)
        for icd in self.reference_service.list_icd10():
            self.icd10.addItem(f"{icd.code} - {icd.title}", str(icd.code))
        self._wire_icd_search(self.icd10)
        self.microbe = QComboBox()
        self.microbe.setEditable(True)
        self.microbe.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.microbe.addItem("Выбрать", None)
        for micro in self.reference_service.list_microorganisms():
            self.microbe.addItem(f"{micro.code or '-'} - {micro.name}", cast(int, micro.id))
        self._wire_micro_search(self.microbe)
        self.antibiotic = QComboBox()
        self.antibiotic.setEditable(True)
        self.antibiotic.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.antibiotic.addItem("Выбрать", None)
        for abx in self.reference_service.list_antibiotics():
            self.antibiotic.addItem(f"{abx.code} - {abx.name}", cast(int, abx.id))
        self._wire_abx_search(self.antibiotic)
        self.material = QComboBox()
        self.material.setEditable(True)
        self.material.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.material.addItem("Выбрать", None)
        for mt in self.reference_service.list_material_types():
            self.material.addItem(f"{mt.code} - {mt.name}", cast(int, mt.id))
        self._wire_material_search(self.material)
        self.growth_flag = QComboBox()
        self.growth_flag.addItem("Выбрать", None)
        self.growth_flag.addItem("Нет", 0)
        self.growth_flag.addItem("Да", 1)
        self.patient_category = QComboBox()
        self.patient_category.addItem("Выбрать", None)
        for value in MilitaryCategory.values():
            self.patient_category.addItem(value, value)
        self.patient_name = QLineEdit()
        self.patient_name.setPlaceholderText("ФИО")
        self.lab_no = QLineEdit()
        self.lab_no.setPlaceholderText("например, MAT-20250101-0001")
        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Поиск по ФИО/МКБ/микроорганизмам")
        for combo in (
            self.department,
            self.icd10,
            self.microbe,
            self.antibiotic,
            self.material,
            self.growth_flag,
            self.patient_category,
        ):
            connect_combo_autowidth(combo)

    def _build_saved_filters_section(self, content_layout: QVBoxLayout) -> None:
        saved_box = QGroupBox("Сохраненные фильтры")
        saved_layout = QHBoxLayout(saved_box)
        self.saved_filter_select = QComboBox()
        self.saved_filter_select.addItem("Выбрать", None)
        connect_combo_autowidth(self.saved_filter_select)
        apply_filter_btn = QPushButton("Применить")
        compact_button(apply_filter_btn)
        apply_filter_btn.clicked.connect(self._apply_saved_filter)
        self.filter_name = QLineEdit()
        self.filter_name.setPlaceholderText("Название фильтра")
        save_filter_btn = QPushButton("Сохранить")
        compact_button(save_filter_btn)
        save_filter_btn.clicked.connect(self._save_filter)
        saved_layout.addWidget(QLabel("Фильтр"))
        saved_layout.addWidget(self.saved_filter_select)
        saved_layout.addWidget(apply_filter_btn)
        saved_layout.addWidget(QLabel("Название"))
        saved_layout.addWidget(self.filter_name)
        saved_layout.addWidget(save_filter_btn)
        self.saved_filters_toggle = QPushButton("Показать сохраненные фильтры ▸")
        compact_button(self.saved_filters_toggle)
        self.saved_filters_toggle.setCheckable(True)
        self.saved_filters_toggle.toggled.connect(self._toggle_saved_filters)
        content_layout.addWidget(self.saved_filters_toggle)

        self.saved_filters_container = QWidget()
        saved_container_layout = QVBoxLayout(self.saved_filters_container)
        saved_container_layout.setContentsMargins(0, 0, 0, 0)
        saved_container_layout.addWidget(saved_box)
        self.saved_filters_container.setVisible(False)
        content_layout.addWidget(self.saved_filters_container)

    def _build_actions_row(self, content_layout: QVBoxLayout) -> None:
        self.search_btn = QPushButton("Поиск")
        self.search_btn.setObjectName("primaryButton")
        compact_button(self.search_btn)
        self.search_btn.clicked.connect(self.on_search)
        self._export_xlsx_btn = QPushButton("Экспорт XLSX")
        compact_button(self._export_xlsx_btn)
        self._export_xlsx_btn.clicked.connect(self._export_xlsx)
        self._export_pdf_btn = QPushButton("Экспорт PDF")
        compact_button(self._export_pdf_btn)
        self._export_pdf_btn.clicked.connect(self._export_pdf)
        self._main_actions_panel = ResponsiveActionsPanel(min_button_width=120, max_columns=4)
        self._main_actions_panel.set_buttons([self.search_btn, self._export_xlsx_btn, self._export_pdf_btn])
        self._main_actions_panel.set_compact(self.width() < 1420)
        content_layout.addWidget(self._main_actions_panel)

    def _build_summary_row(self, content_layout: QVBoxLayout) -> None:
        summary_row = QHBoxLayout()
        summary_row.addWidget(QLabel("Сводка поиска:"))
        self.summary_total = QLabel("Итого: 0")
        self.summary_total.setObjectName("chipLabel")
        self.summary_positive = QLabel("Положительных: 0")
        self.summary_positive.setObjectName("chipLabel")
        self.summary_share = QLabel("Доля: 0%")
        self.summary_share.setObjectName("chipLabel")
        summary_row.addWidget(self.summary_total)
        summary_row.addWidget(self.summary_positive)
        summary_row.addWidget(self.summary_share)
        summary_row.addStretch()
        content_layout.addLayout(summary_row)

    def _build_report_history_section(self, content_layout: QVBoxLayout) -> None:
        history_box = QGroupBox("История отчетов")
        history_layout = QVBoxLayout(history_box)

        filter_row = QHBoxLayout()
        self.report_type_filter = QComboBox()
        self.report_type_filter.addItem("Выбрать", None)
        self.report_type_filter.addItem("Аналитика", "analytics")
        connect_combo_autowidth(self.report_type_filter)
        self.report_type_filter.currentIndexChanged.connect(lambda _index: self._load_report_history())
        self.report_query_filter = QLineEdit()
        self.report_query_filter.setPlaceholderText("Поиск по пути артефакта, SHA256 или фильтрам")
        self.report_query_filter.textChanged.connect(lambda _text: self._load_report_history())
        clear_filters_btn = QPushButton("Сбросить фильтры")
        compact_button(clear_filters_btn)
        clear_filters_btn.clicked.connect(self._clear_report_history_filters)
        filter_row.addWidget(QLabel("Тип"))
        filter_row.addWidget(self.report_type_filter)
        filter_row.addWidget(self.report_query_filter)
        filter_row.addWidget(clear_filters_btn)
        history_layout.addLayout(filter_row)

        refresh_history_btn = QPushButton("Обновить историю")
        compact_button(refresh_history_btn)
        refresh_history_btn.clicked.connect(self._load_report_history)
        verify_all_btn = QPushButton("Проверить хэши")
        compact_button(verify_all_btn)
        verify_all_btn.clicked.connect(lambda: self._load_report_history(verify_hash=True))
        verify_selected_btn = QPushButton("Проверить выбранный")
        compact_button(verify_selected_btn)
        verify_selected_btn.clicked.connect(self._verify_selected_report)
        open_artifact_btn = QPushButton("Открыть артефакт")
        compact_button(open_artifact_btn)
        open_artifact_btn.clicked.connect(self._open_report_artifact)
        self._history_actions_panel = ResponsiveActionsPanel(min_button_width=138, max_columns=4)
        self._history_actions_panel.set_buttons(
            [refresh_history_btn, verify_all_btn, verify_selected_btn, open_artifact_btn]
        )
        self._history_actions_panel.set_compact(self.width() < 1460)
        history_layout.addWidget(self._history_actions_panel)

        self.report_history_table = QTableWidget(0, 8)
        self.report_history_table.setHorizontalHeaderLabels(
            ["ID", "Тип", "Дата", "Пользователь", "Итого", "Верификация", "SHA256", "Артефакт"]
        )
        self.report_history_table.horizontalHeader().setStretchLastSection(True)
        self.report_history_table.verticalHeader().setVisible(False)
        self.report_history_table.setAlternatingRowColors(True)
        self.report_history_table.setSortingEnabled(True)
        self.report_history_table.setMinimumHeight(260)
        self.report_history_table.itemDoubleClicked.connect(self._open_report_artifact)
        history_layout.addWidget(self.report_history_table)
        self._apply_report_history_column_widths()
        content_layout.addWidget(history_box)

    def _build_dashboard_box(self) -> QGroupBox:
        dashboard_box = QGroupBox("Сводка")
        dashboard_layout = QVBoxLayout(dashboard_box)
        compare_row = QHBoxLayout()
        self.compare_period = QComboBox()
        self.compare_period.addItem("Неделя", 7)
        self.compare_period.addItem("Месяц", 30)
        connect_combo_autowidth(self.compare_period)
        self.compare_label = QLabel("Сравнение: -")
        self.compare_label.setObjectName("chipLabel")
        self.dashboard_refresh_btn = QPushButton("Обновить сводку")
        compact_button(self.dashboard_refresh_btn)
        self.dashboard_refresh_btn.clicked.connect(self._update_dashboard)
        self.dashboard_reset_btn = QPushButton("Сбросить фильтры сводки")
        compact_button(self.dashboard_reset_btn)
        self.dashboard_reset_btn.clicked.connect(self._reset_dashboard_filters)
        compare_row.addWidget(QLabel("Период сравнения"))
        compare_row.addWidget(self.compare_period)
        compare_row.addWidget(self.compare_label)
        compare_row.addStretch()
        compare_row.addWidget(self.dashboard_refresh_btn)
        compare_row.addWidget(self.dashboard_reset_btn)
        dashboard_layout.addLayout(compare_row)

        self.department_table = QTableWidget(0, 5)
        self.department_table.setHorizontalHeaderLabels(
            ["Отделение", "Проб", "Положительных", "Доля", "Последняя дата"]
        )
        self.department_table.horizontalHeader().setStretchLastSection(True)
        self.department_table.verticalHeader().setVisible(False)
        self.department_table.setAlternatingRowColors(True)
        self.department_table.setMinimumHeight(240)
        self.department_table.itemChanged.connect(self._on_first_row_changed)
        resize_columns_by_first_row(self.department_table)
        dashboard_layout.addWidget(self.department_table)

        dashboard_layout.addWidget(QLabel("Тренд по периодам"))
        self.trend_chart = TrendChart()
        self.trend_chart.setMinimumHeight(340)
        dashboard_layout.addWidget(self.trend_chart)
        return dashboard_box

    def _build_ismp_box(self) -> QGroupBox:
        ismp_box = QGroupBox("ИСМП показатели")
        ismp_layout = QVBoxLayout(ismp_box)
        ismp_row = QHBoxLayout()
        self.ismp_total_cases = QLabel("Госпитализаций: 0")
        self.ismp_total_cases.setObjectName("chipLabel")
        self.ismp_cases = QLabel("Случаев ИСМП: 0")
        self.ismp_cases.setObjectName("chipLabel")
        self.ismp_incidence = QLabel("Инцидентность: 0.0 на 1000")
        self.ismp_incidence.setObjectName("chipLabel")
        self.ismp_density = QLabel("Плотность: 0.0 на 1000 койко-дн.")
        self.ismp_density.setObjectName("chipLabel")
        self.ismp_prevalence = QLabel("Превалентность: 0.0%")
        self.ismp_prevalence.setObjectName("chipLabel")
        ismp_row.addWidget(self.ismp_total_cases)
        ismp_row.addWidget(self.ismp_cases)
        ismp_row.addWidget(self.ismp_incidence)
        ismp_row.addWidget(self.ismp_density)
        ismp_row.addWidget(self.ismp_prevalence)
        ismp_row.addStretch()
        ismp_layout.addLayout(ismp_row)

        self.ismp_table = QTableWidget(0, 2)
        self.ismp_table.setHorizontalHeaderLabels(["Тип ИСМП", "Количество"])
        self.ismp_table.horizontalHeader().setStretchLastSection(True)
        self.ismp_table.verticalHeader().setVisible(False)
        self.ismp_table.setAlternatingRowColors(True)
        self.ismp_table.setMinimumHeight(160)
        self.ismp_table.itemChanged.connect(self._on_first_row_changed)
        resize_columns_by_first_row(self.ismp_table)
        ismp_layout.addWidget(self.ismp_table)
        return ismp_box

    def _build_top_box(self) -> QGroupBox:
        top_box = QGroupBox("Топ микроорганизмов")
        top_layout = QVBoxLayout(top_box)
        self.chart = TopMicrobesChart()
        self.chart.setMinimumHeight(340)
        top_layout.addWidget(self.chart)
        self.top_table = QTableWidget(0, 2)
        self.top_table.setHorizontalHeaderLabels(["Микроорганизм", "Количество"])
        self.top_table.horizontalHeader().setStretchLastSection(True)
        self.top_table.verticalHeader().setVisible(False)
        self.top_table.setAlternatingRowColors(True)
        self.top_table.setMinimumHeight(220)
        self.top_table.itemChanged.connect(self._on_first_row_changed)
        resize_columns_by_first_row(self.top_table)
        top_layout.addWidget(self.top_table)
        return top_box

    def _build_results_box(self) -> QGroupBox:
        results_box = QGroupBox("Результаты")
        results_layout = QVBoxLayout(results_box)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Лаб. номер",
                "Пациент",
                "Категория",
                "Дата взятия",
                "Отделение",
                "Материал",
                "Микроорганизм",
                "Антибиотик",
            ]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(320)
        self.table.itemChanged.connect(self._on_first_row_changed)
        resize_columns_by_first_row(self.table)
        results_layout.addWidget(self.table)
        return results_box

    def _toggle_saved_filters(self, checked: bool) -> None:
        self.saved_filters_container.setVisible(checked)
        if checked:
            self.saved_filters_toggle.setText("Скрыть сохраненные фильтры ▾")
        else:
            self.saved_filters_toggle.setText("Показать сохраненные фильтры ▸")

    def _wire_icd_search(self, combo: QComboBox) -> None:
        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)

        editor = combo.lineEdit()
        if editor is None:
            return

        editor.textEdited.connect(self._schedule_icd_refresh)
        self._icd_combo = combo

    def _refresh_icd_combo(self, combo: QComboBox, text: str) -> None:
        current_data = combo.currentData()
        query = text.strip()
        if query:
            icd_list = self.reference_service.search_icd10(query, limit=50)
        else:
            icd_list = self.reference_service.list_icd10()

        with QSignalBlocker(combo):
            combo.clear()
            combo.addItem("Выбрать", None)
            for icd in icd_list:
                combo.addItem(f"{icd.code} - {icd.title}", str(icd.code))
            if current_data is not None:
                idx = combo.findData(current_data)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.setEditText(text)

    def _wire_micro_search(self, combo: QComboBox) -> None:
        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)

        editor = combo.lineEdit()
        if editor is None:
            return

        editor.textEdited.connect(self._schedule_micro_refresh)
        self._micro_combo = combo

    def _refresh_micro_combo(self, combo: QComboBox, text: str) -> None:
        current_data = combo.currentData()
        query = text.strip()
        if query:
            micro_list = self.reference_service.search_microorganisms(query, limit=50)
        else:
            micro_list = self.reference_service.list_microorganisms()

        with QSignalBlocker(combo):
            combo.clear()
            combo.addItem("Выбрать", None)
            for micro in micro_list:
                combo.addItem(f"{micro.code or '-'} - {micro.name}", cast(int, micro.id))
            if current_data is not None:
                idx = combo.findData(current_data)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.setEditText(text)

    def _wire_abx_search(self, combo: QComboBox) -> None:
        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)

        editor = combo.lineEdit()
        if editor is None:
            return

        editor.textEdited.connect(self._schedule_abx_refresh)
        self._abx_combo = combo

    def _refresh_abx_combo(self, combo: QComboBox, text: str) -> None:
        current_data = combo.currentData()
        query = text.strip()
        if query:
            abx_list = self.reference_service.search_antibiotics(query, limit=50)
        else:
            abx_list = self.reference_service.list_antibiotics()

        with QSignalBlocker(combo):
            combo.clear()
            combo.addItem("Выбрать", None)
            for abx in abx_list:
                combo.addItem(f"{abx.code} - {abx.name}", cast(int, abx.id))
            if current_data is not None:
                idx = combo.findData(current_data)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.setEditText(text)

    def _wire_material_search(self, combo: QComboBox) -> None:
        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)

        editor = combo.lineEdit()
        if editor is None:
            return

        editor.textEdited.connect(self._schedule_material_refresh)
        self._material_combo = combo

    def _refresh_material_combo(self, combo: QComboBox, text: str) -> None:
        current_data = combo.currentData()
        query = text.strip()
        if query:
            material_list = self.reference_service.search_material_types(query, limit=50)
        else:
            material_list = self.reference_service.list_material_types()

        with QSignalBlocker(combo):
            combo.clear()
            combo.addItem("Выбрать", None)
            for mt in material_list:
                combo.addItem(f"{mt.code} - {mt.name}", cast(int, mt.id))
            if current_data is not None:
                idx = combo.findData(current_data)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.setEditText(text)

    def _schedule_icd_refresh(self, text: str) -> None:
        self._icd_pending_text = text
        self._icd_search_timer.start(self._search_delay_ms)

    def _trigger_icd_refresh(self) -> None:
        if self._icd_search_updating:
            return
        combo = getattr(self, "_icd_combo", None)
        if not isinstance(combo, QComboBox):
            return
        self._icd_search_updating = True
        try:
            self._refresh_icd_combo(combo, self._icd_pending_text)
        finally:
            self._icd_search_updating = False

    def _schedule_micro_refresh(self, text: str) -> None:
        self._micro_pending_text = text
        self._micro_search_timer.start(self._search_delay_ms)

    def _trigger_micro_refresh(self) -> None:
        if self._micro_search_updating:
            return
        combo = getattr(self, "_micro_combo", None)
        if not isinstance(combo, QComboBox):
            return
        self._micro_search_updating = True
        try:
            self._refresh_micro_combo(combo, self._micro_pending_text)
        finally:
            self._micro_search_updating = False

    def _schedule_abx_refresh(self, text: str) -> None:
        self._abx_pending_text = text
        self._abx_search_timer.start(self._search_delay_ms)

    def _trigger_abx_refresh(self) -> None:
        if self._abx_search_updating:
            return
        combo = getattr(self, "_abx_combo", None)
        if not isinstance(combo, QComboBox):
            return
        self._abx_search_updating = True
        try:
            self._refresh_abx_combo(combo, self._abx_pending_text)
        finally:
            self._abx_search_updating = False

    def _schedule_material_refresh(self, text: str) -> None:
        self._material_pending_text = text
        self._material_search_timer.start(self._search_delay_ms)

    def _trigger_material_refresh(self) -> None:
        if self._material_search_updating:
            return
        combo = getattr(self, "_material_combo", None)
        if not isinstance(combo, QComboBox):
            return
        self._material_search_updating = True
        try:
            self._refresh_material_combo(combo, self._material_pending_text)
        finally:
            self._material_search_updating = False

    def refresh_references(self) -> None:
        current_dep = self.department.currentData()
        current_icd = self.icd10.currentData()
        icd_text = self.icd10.currentText()
        current_micro = self.microbe.currentData()
        micro_text = self.microbe.currentText()
        current_abx = self.antibiotic.currentData()
        abx_text = self.antibiotic.currentText()
        current_material = self.material.currentData()
        material_text = self.material.currentText()
        current_growth = self.growth_flag.currentData()
        current_category = self.patient_category.currentData()

        self.department.blockSignals(True)
        self.department.clear()
        self.department.addItem("Выбрать", None)
        for dep in self.reference_service.list_departments():
            self.department.addItem(str(dep.name), cast(int, dep.id))
        if current_dep is not None:
            idx = self.department.findData(current_dep)
            if idx >= 0:
                self.department.setCurrentIndex(idx)
        self.department.blockSignals(False)

        self._refresh_icd_combo(self.icd10, icd_text)
        if current_icd is not None:
            idx = self.icd10.findData(current_icd)
            if idx >= 0:
                self.icd10.setCurrentIndex(idx)

        self._refresh_micro_combo(self.microbe, micro_text)
        if current_micro is not None:
            idx = self.microbe.findData(current_micro)
            if idx >= 0:
                self.microbe.setCurrentIndex(idx)

        self._refresh_abx_combo(self.antibiotic, abx_text)
        if current_abx is not None:
            idx = self.antibiotic.findData(current_abx)
            if idx >= 0:
                self.antibiotic.setCurrentIndex(idx)

        self._refresh_material_combo(self.material, material_text)
        if current_material is not None:
            idx = self.material.findData(current_material)
            if idx >= 0:
                self.material.setCurrentIndex(idx)

        self.growth_flag.blockSignals(True)
        self.growth_flag.clear()
        self.growth_flag.addItem("Выбрать", None)
        self.growth_flag.addItem("Нет", 0)
        self.growth_flag.addItem("Да", 1)
        if current_growth is not None:
            idx = self.growth_flag.findData(current_growth)
            if idx >= 0:
                self.growth_flag.setCurrentIndex(idx)
        self.growth_flag.blockSignals(False)

        self.patient_category.blockSignals(True)
        self.patient_category.clear()
        self.patient_category.addItem("Выбрать", None)
        for value in MilitaryCategory.values():
            self.patient_category.addItem(value, value)
        if current_category is not None:
            idx = self.patient_category.findData(current_category)
            if idx >= 0:
                self.patient_category.setCurrentIndex(idx)
        self.patient_category.blockSignals(False)

        for combo in (
            self.department,
            self.icd10,
            self.microbe,
            self.antibiotic,
            self.material,
            self.growth_flag,
            self.patient_category,
        ):
            connect_combo_autowidth(combo)

    def on_search(self) -> None:
        req = self._build_request()
        self._run_search_async(req)

    def _build_request(self) -> AnalyticsSearchRequest:
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

    def _set_export_busy(self, busy: bool) -> None:
        self._export_xlsx_btn.setEnabled(not busy)
        self._export_pdf_btn.setEnabled(not busy)

    def _set_search_busy(self, busy: bool) -> None:
        self.search_btn.setEnabled(not busy)
        self._set_export_busy(busy)

    def _set_dashboard_busy(self, busy: bool) -> None:
        self.dashboard_refresh_btn.setEnabled(not busy)
        self.dashboard_reset_btn.setEnabled(not busy)

    def _run_search_async(self, req: AnalyticsSearchRequest) -> None:
        self._set_search_busy(True)
        self._set_dashboard_busy(True)
        date_from, date_to = self._get_period_range()
        compare_days = int(self.compare_period.currentData() or 7)
        patient_category = self.patient_category.currentData()
        department_id = self.department.currentData()

        def _run() -> dict:
            rows = self.analytics_service.search_samples(req)
            agg = self.analytics_service.get_aggregates(req)
            dashboard = self._fetch_dashboard_data(
                date_from=date_from,
                date_to=date_to,
                patient_category=patient_category,
                department_id=department_id,
                compare_days=compare_days,
            )
            return {"rows": rows, "agg": agg, "dashboard": dashboard}

        def _on_success(result: dict) -> None:
            self._apply_search_results(result["rows"], result["agg"])
            self._apply_dashboard_data(result["dashboard"])

        def _on_finished() -> None:
            self._set_search_busy(False)
            self._set_dashboard_busy(False)

        run_async(
            self,
            _run,
            on_success=_on_success,
            on_error=lambda exc: show_error(self, str(exc)),
            on_finished=_on_finished,
        )

    def _apply_search_results(self, rows: list, agg: dict) -> None:
        self.summary_total.setText(f"Итого: {agg['total']}")
        self.summary_positive.setText(f"Положительных: {agg['positives']}")
        self.summary_share.setText(f"Доля: {agg['positive_share'] * 100:.1f}%")
        self.chart.update_data(agg["top_microbes"])
        self.top_table.clearContents()
        self.top_table.setRowCount(len(agg["top_microbes"]))
        for idx, (name, count) in enumerate(agg["top_microbes"]):
            self.top_table.setItem(idx, 0, QTableWidgetItem(name))
            self.top_table.setItem(idx, 1, QTableWidgetItem(str(count)))
        resize_columns_by_first_row(self.top_table)
        self.table.clearContents()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(r.lab_sample_id)))
            self.table.setItem(i, 1, QTableWidgetItem(r.lab_no))
            self.table.setItem(i, 2, QTableWidgetItem(r.patient_name))
            self.table.setItem(i, 3, QTableWidgetItem(r.patient_category or ""))
            self.table.setItem(i, 4, QTableWidgetItem(format_analytics_datetime(r.taken_at)))
            self.table.setItem(i, 5, QTableWidgetItem(r.department_name or ""))
            self.table.setItem(i, 6, QTableWidgetItem(r.material_type or ""))
            self.table.setItem(i, 7, QTableWidgetItem(r.microorganism or ""))
            self.table.setItem(i, 8, QTableWidgetItem(r.antibiotic or ""))
        resize_columns_by_first_row(self.table)

    def _export_xlsx(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(self, "Экспорт XLSX", "analytics_report.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        req = self._build_request()
        self._set_export_busy(True)

        def _run() -> dict:
            return self.reporting_service.export_analytics_xlsx(
                request=req,
                file_path=path,
                actor_id=self.session.user_id,
            )

        def _on_success(result: dict) -> None:
            show_info(self, f"Экспорт завершен: {result['count']} строк")
            self._load_report_history()

        run_async(
            self,
            _run,
            on_success=_on_success,
            on_error=lambda exc: show_error(self, str(exc)),
            on_finished=lambda: self._set_export_busy(False),
        )

    def _export_pdf(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(self, "Экспорт PDF", "analytics_report.pdf", "PDF (*.pdf)")
        if not path:
            return
        req = self._build_request()
        self._set_export_busy(True)

        def _run() -> dict:
            return self.reporting_service.export_analytics_pdf(
                request=req,
                file_path=path,
                actor_id=self.session.user_id,
            )

        def _on_success(result: dict) -> None:
            show_info(self, f"Экспорт завершен: {result['count']} строк")
            self._load_report_history()

        run_async(
            self,
            _run,
            on_success=_on_success,
            on_error=lambda exc: show_error(self, str(exc)),
            on_finished=lambda: self._set_export_busy(False),
        )

    def _on_first_row_changed(self, item: QTableWidgetItem) -> None:
        if item and item.row() == 0:
            table = item.tableWidget()
            if table is not None:
                resize_columns_by_first_row(table)

    def _load_report_history(self, verify_hash: bool = False) -> None:
        try:
            rows = self.reporting_service.list_report_runs(
                limit=100,
                report_type=self.report_type_filter.currentData(),
                query=self.report_query_filter.text().strip() or None,
                verify_hash=verify_hash,
            )
        except Exception as exc:  # noqa: BLE001
            show_error(self, str(exc))
            return

        self.report_history_table.clearContents()
        self.report_history_table.setRowCount(len(rows))
        for i, item in enumerate(rows):
            row_data = to_report_history_view_row(item)
            id_item = QTableWidgetItem(str(row_data.report_run_id))
            id_item.setData(Qt.ItemDataRole.UserRole, row_data.report_run_id)
            self.report_history_table.setItem(i, 0, id_item)
            self.report_history_table.setItem(i, 1, QTableWidgetItem(row_data.report_type))
            self.report_history_table.setItem(i, 2, QTableWidgetItem(row_data.created_text))
            self.report_history_table.setItem(i, 3, QTableWidgetItem(row_data.created_by))
            self.report_history_table.setItem(i, 4, QTableWidgetItem(row_data.total_text))
            self.report_history_table.setItem(i, 5, QTableWidgetItem(row_data.verification_text))
            self.report_history_table.setItem(i, 6, QTableWidgetItem(row_data.artifact_sha256))
            path_item = QTableWidgetItem(row_data.artifact_path)
            path_item.setToolTip(row_data.artifact_path)
            self.report_history_table.setItem(i, 7, path_item)
        resize_columns_by_first_row(self.report_history_table)
        self._apply_report_history_column_widths()

    def _apply_report_history_column_widths(self) -> None:
        for column, width in report_history_column_widths().items():
            self.report_history_table.setColumnWidth(column, width)

    def _clear_report_history_filters(self) -> None:
        self.report_type_filter.setCurrentIndex(0)
        self.report_query_filter.clear()
        self._load_report_history()

    def _open_report_artifact(self) -> None:
        row = self.report_history_table.currentRow()
        if row < 0:
            show_warning(self, "Выберите строку в истории отчетов.")
            return
        path_item = self.report_history_table.item(row, 7)
        if not path_item or not path_item.text().strip():
            show_warning(self, "Путь к артефакту не указан.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path_item.text().strip()))

    def _verify_selected_report(self) -> None:
        row = self.report_history_table.currentRow()
        if row < 0:
            show_warning(self, "Выберите строку в истории отчетов.")
            return
        id_item = self.report_history_table.item(row, 0)
        report_run_id = cast(int | None, id_item.data(Qt.ItemDataRole.UserRole) if id_item else None)
        if report_run_id is None:
            show_warning(self, "Не удалось определить запись отчета.")
            return
        try:
            result = self.reporting_service.verify_report_run(int(report_run_id))
        except Exception as exc:  # noqa: BLE001
            show_error(self, str(exc))
            return
        self.report_history_table.setItem(row, 5, QTableWidgetItem(format_report_verification(result)))
        status = str(result.get("status") or "")
        message = str(result.get("message") or "Проверка завершена")
        if status == "ok":
            show_info(self, message)
        else:
            show_warning(self, message)

    def _collect_filter_payload(self) -> dict:
        payload: dict[str, object] = {}
        date_from = self.date_from.date().toString("dd.MM.yyyy")
        date_to = self.date_to.date().toString("dd.MM.yyyy")
        if date_from:
            payload["date_from"] = date_from
        if date_to:
            payload["date_to"] = date_to

        if self.department.currentData() is not None:
            payload["department_id"] = self.department.currentData()
        if self.icd10.currentData() is not None:
            payload["icd10_code"] = self.icd10.currentData()
        if self.microbe.currentData() is not None:
            payload["microorganism_id"] = self.microbe.currentData()
        if self.antibiotic.currentData() is not None:
            payload["antibiotic_id"] = self.antibiotic.currentData()
        if self.material.currentData() is not None:
            payload["material_type_id"] = self.material.currentData()
        if self.growth_flag.currentData() is not None:
            payload["growth_flag"] = self.growth_flag.currentData()
        if self.patient_category.currentData() is not None:
            payload["patient_category"] = self.patient_category.currentData()

        if self.patient_name.text().strip():
            payload["patient_name"] = self.patient_name.text().strip()
        if self.lab_no.text().strip():
            payload["lab_no"] = self.lab_no.text().strip()
        if self.search_text.text().strip():
            payload["search_text"] = self.search_text.text().strip()

        return payload

    def _apply_filter_payload(self, payload: dict) -> None:
        if payload.get("date_from"):
            qdate = QDate.fromString(str(payload["date_from"]), "dd.MM.yyyy")
            if not qdate.isValid():
                qdate = QDate.fromString(str(payload["date_from"]), "yyyy-MM-dd")
            if qdate.isValid():
                self.date_from.setDate(qdate)
        if payload.get("date_to"):
            qdate = QDate.fromString(str(payload["date_to"]), "dd.MM.yyyy")
            if not qdate.isValid():
                qdate = QDate.fromString(str(payload["date_to"]), "yyyy-MM-dd")
            if qdate.isValid():
                self.date_to.setDate(qdate)

        if "department_id" in payload:
            self.department.setCurrentIndex(self.department.findData(payload["department_id"]))
        if "icd10_code" in payload:
            self.icd10.setCurrentIndex(self.icd10.findData(payload["icd10_code"]))
        if "microorganism_id" in payload:
            self.microbe.setCurrentIndex(self.microbe.findData(payload["microorganism_id"]))
        if "antibiotic_id" in payload:
            self.antibiotic.setCurrentIndex(self.antibiotic.findData(payload["antibiotic_id"]))
        if "material_type_id" in payload:
            self.material.setCurrentIndex(self.material.findData(payload["material_type_id"]))
        if "growth_flag" in payload:
            self.growth_flag.setCurrentIndex(self.growth_flag.findData(payload["growth_flag"]))
        if "patient_category" in payload:
            self.patient_category.setCurrentIndex(self.patient_category.findData(payload["patient_category"]))

        self.patient_name.setText(payload.get("patient_name", "") or "")
        self.lab_no.setText(payload.get("lab_no", "") or "")
        self.search_text.setText(payload.get("search_text", "") or "")

    def _load_saved_filters(self) -> None:
        self.saved_filter_select.clear()
        self.saved_filter_select.addItem("Выбрать", None)
        try:
            filters = self.saved_filter_service.list_filters("analytics")
        except Exception as exc:  # noqa: BLE001
            show_error(self, str(exc))
            return
        for item in filters:
            self.saved_filter_select.addItem(str(item.name), str(item.payload_json))
        connect_combo_autowidth(self.saved_filter_select)

    def _save_filter(self) -> None:
        name = self.filter_name.text().strip()
        payload = self._collect_filter_payload()
        try:
            self.saved_filter_service.save_filter(
                filter_type="analytics",
                name=name,
                payload=payload,
                created_by=self.session.user_id,
            )
        except ValueError as exc:
            show_warning(self, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            show_error(self, str(exc))
            return
        self._load_saved_filters()
        self.filter_name.clear()
        show_info(self, "Фильтр сохранен")

    def _apply_saved_filter(self) -> None:
        payload_json = self.saved_filter_select.currentData()
        if not payload_json:
            show_warning(self, "Выберите сохраненный фильтр")
            return
        try:
            payload = json.loads(payload_json)
        except Exception as exc:  # noqa: BLE001
            show_error(self, f"Невозможно прочитать фильтр: {exc}")
            return
        self._apply_filter_payload(payload)

    def _update_dashboard(self) -> None:
        date_from, date_to = self._get_period_range()
        compare_days = int(self.compare_period.currentData() or 7)
        patient_category = self.patient_category.currentData()
        department_id = self.department.currentData()
        self._set_dashboard_busy(True)

        def _run() -> dict:
            return self._fetch_dashboard_data(
                date_from=date_from,
                date_to=date_to,
                patient_category=patient_category,
                department_id=department_id,
                compare_days=compare_days,
            )

        def _on_success(data: dict) -> None:
            self._apply_dashboard_data(data)

        run_async(
            self,
            _run,
            on_success=_on_success,
            on_error=lambda exc: show_error(self, str(exc)),
            on_finished=lambda: self._set_dashboard_busy(False),
        )

    def _fetch_dashboard_data(
        self,
        date_from: date | None,
        date_to: date | None,
        patient_category: str | None,
        department_id: int | None,
        compare_days: int,
    ) -> dict:
        department_rows = self.analytics_service.get_department_summary(
            date_from, date_to, patient_category=patient_category
        )
        trend_rows = self.analytics_service.get_trend_by_day(
            date_from, date_to, patient_category=patient_category
        )
        compare = None
        if date_to is not None:
            current_from, current_to, prev_from, prev_to = calculate_compare_window(date_to, compare_days)
            compare = self.analytics_service.compare_periods(
                current_from=current_from,
                current_to=current_to,
                prev_from=prev_from,
                prev_to=prev_to,
                patient_category=patient_category,
            )
        ismp = self.analytics_service.get_ismp_metrics(date_from, date_to, department_id)
        return {
            "department_rows": department_rows,
            "trend_rows": trend_rows,
            "compare": compare,
            "end_date": date_to,
            "ismp": ismp,
        }

    def _apply_dashboard_data(self, data: dict) -> None:
        self._apply_department_summary(data.get("department_rows", []))
        self._apply_trend(data.get("trend_rows", []))
        self._apply_compare(data.get("compare"), data.get("end_date"))
        self._apply_ismp_metrics(data.get("ismp", {}))

    def _update_ismp_metrics(self, date_from, date_to) -> None:
        department_id = self.department.currentData()
        data = self.analytics_service.get_ismp_metrics(date_from, date_to, department_id)
        self._apply_ismp_metrics(data)

    def _apply_quick_period(self) -> None:
        today = QDate.currentDate()
        mode = self.quick_period.currentData()
        today_py = cast(date, today.toPython())
        date_from, date_to = quick_period_bounds(cast(str | None, mode), today_py)
        self.date_from.setDate(QDate(date_from.year, date_from.month, date_from.day))
        self.date_to.setDate(QDate(date_to.year, date_to.month, date_to.day))

    def _reset_search_filters(self) -> None:
        today = QDate.currentDate()
        self.date_from.setDate(today)
        self.date_to.setDate(today)
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
        if self.saved_filter_select.count() > 0:
            self.saved_filter_select.setCurrentIndex(0)

    def _get_period_range(self) -> tuple:
        date_from = cast(date | None, self.date_from.date().toPython())
        date_to = cast(date | None, self.date_to.date().toPython())
        return normalize_date_range(date_from, date_to)

    def _update_department_summary(self, date_from, date_to) -> None:
        rows = self.analytics_service.get_department_summary(
            date_from, date_to, patient_category=self.patient_category.currentData()
        )
        self._apply_department_summary(rows)

    def _update_trend(self, date_from, date_to) -> None:
        rows = self.analytics_service.get_trend_by_day(
            date_from, date_to, patient_category=self.patient_category.currentData()
        )
        self._apply_trend(rows)

    def _update_compare(self, end_date) -> None:
        if end_date is None:
            self.compare_label.setText("Сравнение: -")
            return
        days = int(self.compare_period.currentData() or 7)
        current_from, current_to, prev_from, prev_to = calculate_compare_window(end_date, days)

        compare = self.analytics_service.compare_periods(
            current_from=current_from,
            current_to=current_to,
            prev_from=prev_from,
            prev_to=prev_to,
            patient_category=self.patient_category.currentData(),
        )
        self._apply_compare(compare, end_date)

    def _apply_department_summary(self, rows: list[dict]) -> None:
        self.department_table.clearContents()
        self.department_table.setRowCount(len(rows))
        for idx, item in enumerate(rows):
            self.department_table.setItem(idx, 0, QTableWidgetItem(item["department_name"]))
            self.department_table.setItem(idx, 1, QTableWidgetItem(str(item["total"])))
            self.department_table.setItem(idx, 2, QTableWidgetItem(str(item["positives"])))
            self.department_table.setItem(
                idx, 3, QTableWidgetItem(f"{item['positive_share'] * 100:.1f}%")
            )
            last_dt = item["last_date"]
            last_date = last_dt.strftime("%d.%m.%Y") if last_dt else ""
            self.department_table.setItem(idx, 4, QTableWidgetItem(last_date))
        resize_columns_by_first_row(self.department_table)

    def _apply_trend(self, rows: list[dict]) -> None:
        items = []
        for item in rows:
            day_label = format_day_label(item.get("day"))
            items.append((day_label, item["total"], item["positives"]))
        self.trend_chart.update_data(items)

    def _apply_compare(self, compare: dict | None, end_date: date | None) -> None:
        if end_date is None or not compare:
            self.compare_label.setText("Сравнение: -")
            return
        current = compare["current"]
        previous = compare["previous"]
        self.compare_label.setText(
            f"Текущий: {current['total']} / {current['positive_share'] * 100:.1f}% · "
            f"Предыдущий: {previous['total']} / {previous['positive_share'] * 100:.1f}%"
        )

    def _apply_ismp_metrics(self, data: dict) -> None:
        if not data:
            self.ismp_total_cases.setText("Госпитализаций: 0")
            self.ismp_cases.setText("Случаев ИСМП: 0")
            self.ismp_incidence.setText("Инцидентность: 0.0 на 1000")
            self.ismp_density.setText("Плотность: 0.0 на 1000 койко-дн.")
            self.ismp_prevalence.setText("Превалентность: 0.0%")
            self.ismp_table.setRowCount(0)
            return
        self.ismp_total_cases.setText(f"Госпитализаций: {data['total_cases']}")
        self.ismp_cases.setText(f"Случаев ИСМП: {data['ismp_cases']}")
        self.ismp_incidence.setText(f"Инцидентность: {data['incidence']:.1f} на 1000")
        self.ismp_density.setText(
            f"Плотность: {data['incidence_density']:.1f} на 1000 койко-дн."
        )
        self.ismp_prevalence.setText(f"Превалентность: {data['prevalence']:.1f}%")

        self.ismp_table.clearContents()
        rows = data["by_type"]
        self.ismp_table.setRowCount(len(rows))
        for idx, item in enumerate(rows):
            self.ismp_table.setItem(idx, 0, QTableWidgetItem(item["type"]))
            self.ismp_table.setItem(idx, 1, QTableWidgetItem(str(item["count"])))
        resize_columns_by_first_row(self.ismp_table)

    def _reset_dashboard_filters(self) -> None:
        today = QDate.currentDate()
        self.date_from.setDate(today)
        self.date_to.setDate(today)
        self.compare_period.setCurrentIndex(0)
        self.patient_category.setCurrentIndex(0)
        self._update_dashboard()
