from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from PySide6.QtCore import QDate, QDateTime, QSignalBlocker, Qt, QTime
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
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

from app.application.dto.lab_dto import (
    LabSampleCreateRequest,
    LabSampleResultUpdate,
    LabSampleUpdateRequest,
)
from app.application.services.lab_service import LabService
from app.application.services.reference_service import ReferenceService
from app.ui.lab.lab_sample_detail_helpers import (
    PhageInput,
    SusceptibilityInput,
    build_phage_payload,
    build_susceptibility_payload,
    compose_lab_result_update,
    has_lab_result_data,
)
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import clear_status, set_status
from app.ui.widgets.table_utils import (
    connect_combo_autowidth,
    connect_combo_resize_on_first_row,
    resize_columns_by_first_row,
)


class LabSampleDetailDialog(QDialog):
    def __init__(
        self,
        lab_service: LabService,
        reference_service: ReferenceService,
        patient_id: int,
        emr_case_id: int | None,
        sample_id: int | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.lab_service = lab_service
        self.reference_service = reference_service
        self.patient_id = patient_id
        self.emr_case_id = emr_case_id
        self.sample_id: int | None = sample_id
        self._abx_list: list[Any] = []
        self._phage_list: list[Any] = []
        self._micro_search_updating = False
        self.setWindowTitle("Лабораторная проба")
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setSizeGripEnabled(True)
        self.resize(1100, 980)
        self.setMinimumSize(900, 700)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(12)

        main_title = QLabel("Карточка лабораторной пробы")
        main_title.setObjectName("sectionTitle")
        content_layout.addWidget(main_title)

        # Основные данные
        self.material_type = QComboBox()
        self.material_type.setEditable(False)
        self.material_type.addItem("Выбрать", None)
        self.taken_at = QDateTimeEdit()
        self.taken_at.setDisplayFormat("dd.MM.yyyy HH:mm")
        if not hasattr(self, "ordered_at"):
            self.ordered_at = QDateTimeEdit()
        self.ordered_at.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.delivered_at = QDateTimeEdit()
        self.delivered_at.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.study_kind = QComboBox()
        self.study_kind.addItem("Выбрать", None)
        self.study_kind.addItem("Первичное", "primary")
        self.study_kind.addItem("Повторное", "repeat")
        self.material_location = QLineEdit()
        self.medium = QLineEdit()
        min_dt = QDateTime(QDate(2024, 1, 1), QTime(0, 0))
        self.ordered_at.setMinimumDateTime(min_dt)
        self.taken_at.setMinimumDateTime(min_dt)
        self.delivered_at.setMinimumDateTime(min_dt)
        # Keep editable even when editing existing sample.

        main_box = QGroupBox("Основные данные")
        main_box.setCheckable(True)
        main_box.setChecked(True)
        main_content = QWidget()
        main_form = QFormLayout(main_content)
        main_form.addRow("Тип материала", self.material_type)
        main_form.addRow("Время взятия", self.taken_at)
        main_form.addRow("Тип исследования", self.study_kind)
        main_form.addRow("Место забора", self.material_location)
        main_form.addRow("Среда", self.medium)
        main_form.addRow("Дата назначения", self.ordered_at)
        main_form.addRow("Дата доставки", self.delivered_at)

        main_layout = QVBoxLayout(main_box)

        main_layout.addWidget(main_content)
        main_box.toggled.connect(main_content.setVisible)
        content_layout.addWidget(main_box)

        # Результаты роста
        self.growth_flag = QComboBox()
        self.growth_flag.addItem("Выбрать", None)
        self.growth_flag.addItem("Нет", 0)
        self.growth_flag.addItem("Да", 1)
        self.growth_result_at = QDateTimeEdit()
        self.growth_result_at.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.growth_result_at.setMinimumDateTime(min_dt)
        self.colony_desc = QLineEdit()
        self.microscopy = QLineEdit()
        self.cfu = QLineEdit()

        result_box = QGroupBox("Результаты роста")
        result_box.setCheckable(True)
        result_box.setChecked(True)
        result_content = QWidget()
        result_form = QFormLayout(result_content)
        result_form.addRow("Рост", self.growth_flag)
        result_form.addRow("Результат от", self.growth_result_at)
        result_form.addRow("Колонии/морфология", self.colony_desc)
        result_form.addRow("Микроскопия", self.microscopy)
        result_form.addRow("КОЕ", self.cfu)
        result_layout = QVBoxLayout(result_box)
        result_layout.addWidget(result_content)
        result_box.toggled.connect(result_content.setVisible)
        content_layout.addWidget(result_box)

        # Контроль качества
        self.qc_status = QComboBox()
        self.qc_status.addItem("Выберите статус QC", None)
        self.qc_status.addItem("Допустимо", "valid")
        self.qc_status.addItem("Условно", "conditional")
        self.qc_status.addItem("Брак", "rejected")
        self.qc_status.setItemData(0, 0, Qt.ItemDataRole.UserRole - 1)
        self.qc_due_at = QLabel("-")
        self.qc_due_at.setObjectName("muted")

        qc_box = QGroupBox("Контроль качества")
        qc_box.setCheckable(True)
        qc_box.setChecked(True)
        qc_content = QWidget()
        qc_form = QFormLayout(qc_content)
        qc_form.addRow("Статус QC", self.qc_status)
        qc_form.addRow("Срок QC", self.qc_due_at)
        qc_layout = QVBoxLayout(qc_box)
        qc_layout.addWidget(qc_content)
        qc_box.toggled.connect(qc_content.setVisible)
        content_layout.addWidget(qc_box)

        # Идентификация
        self.micro_combo = QComboBox()
        self.micro_combo.setEditable(True)
        self.micro_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.micro_combo.addItem("Выбрать", None)
        self.micro_free = QLineEdit()
        self.micro_free.setPlaceholderText("если нет в справочнике")

        micro_box = QGroupBox("Идентификация")
        micro_box.setCheckable(True)
        micro_box.setChecked(True)
        micro_content = QWidget()
        micro_form = QFormLayout(micro_content)
        micro_form.addRow("Микроорганизм", self.micro_combo)
        micro_form.addRow("Микроорганизм (свободно)", self.micro_free)
        micro_layout = QVBoxLayout(micro_box)
        micro_layout.addWidget(micro_content)
        micro_box.toggled.connect(micro_content.setVisible)
        content_layout.addWidget(micro_box)

        # Панели
        self.susc_table = self._make_table(["Антибиотик", "RIS", "MIC", "Метод"], 1)
        self._increase_table_height(self.susc_table)
        self.phage_table = self._make_table(["Фаг", "Свободное имя", "Диаметр"], 1)
        self._increase_table_height(self.phage_table)

        susc_box = QGroupBox("Чувствительность (RIS/MIC)")
        susc_box.setCheckable(True)
        susc_box.setChecked(True)
        susc_content = QWidget()
        susc_layout = QVBoxLayout(susc_content)
        susc_layout.addWidget(self.susc_table)
        susc_controls = QHBoxLayout()
        susc_add_btn = QPushButton("Добавить строку")
        compact_button(susc_add_btn)
        susc_add_btn.clicked.connect(self._add_susc_row)
        susc_del_btn = QPushButton("Удалить строку")
        compact_button(susc_del_btn)
        susc_del_btn.clicked.connect(lambda: self._delete_table_row(self.susc_table))
        susc_controls.addWidget(susc_add_btn)
        susc_controls.addWidget(susc_del_btn)
        susc_controls.addStretch()
        susc_layout.addLayout(susc_controls)
        susc_box_layout = QVBoxLayout(susc_box)
        susc_box_layout.addWidget(susc_content)
        susc_box.toggled.connect(susc_content.setVisible)
        content_layout.addWidget(susc_box)

        phage_box = QGroupBox("Панель фагов")
        phage_box.setCheckable(True)
        phage_box.setChecked(True)
        phage_content = QWidget()
        phage_layout = QVBoxLayout(phage_content)
        phage_layout.addWidget(self.phage_table)
        phage_controls = QHBoxLayout()
        phage_add_btn = QPushButton("Добавить строку")
        compact_button(phage_add_btn)
        phage_add_btn.clicked.connect(self._add_phage_row)
        phage_del_btn = QPushButton("Удалить строку")
        compact_button(phage_del_btn)
        phage_del_btn.clicked.connect(lambda: self._delete_table_row(self.phage_table))
        phage_controls.addWidget(phage_add_btn)
        phage_controls.addWidget(phage_del_btn)
        phage_controls.addStretch()
        phage_layout.addLayout(phage_controls)
        phage_box_layout = QVBoxLayout(phage_box)
        phage_box_layout.addWidget(phage_content)
        phage_box.toggled.connect(phage_content.setVisible)
        content_layout.addWidget(phage_box)

        template_row = QHBoxLayout()
        template_btn = QPushButton("Заполнить шаблоны")
        compact_button(template_btn)
        template_btn.setToolTip("Заполнить RIS и значения фагов по умолчанию для выбранных строк.")
        template_btn.clicked.connect(self._apply_default_templates)
        template_row.addWidget(template_btn)
        template_row.addStretch()
        content_layout.addLayout(template_row)

        self.error_label = QLabel()
        set_status(self.error_label, "", "info")
        content_layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_btn:
            save_btn.setText("Сохранить")
            save_btn.setObjectName("primaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.on_save)
        buttons.rejected.connect(self.reject)
        content_layout.addWidget(buttons)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._load_material_types()
        self._load_microbes()
        self._setup_abx_rows()
        self._setup_phage_rows()
        if self.sample_id:
            self._load_existing()

    def _load_material_types(self) -> None:
        try:
            self.material_type.clear()
            self.material_type.addItem("Выбрать", None)
            for mt in self.reference_service.list_material_types():
                self.material_type.addItem(f"{mt.code} - {mt.name}", mt.id)
            connect_combo_autowidth(self.material_type)
        except Exception as exc:  # noqa: BLE001
            set_status(self.error_label, str(exc), "error")

    def _load_microbes(self) -> None:
        try:
            self._refresh_micro_combo("")
            self._configure_micro_search()
            connect_combo_autowidth(self.micro_combo)
        except Exception as exc:  # noqa: BLE001
            set_status(self.error_label, str(exc), "error")

    def _configure_micro_search(self) -> None:
        completer = QCompleter(self.micro_combo.model(), self.micro_combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.micro_combo.setCompleter(completer)
        editor = self.micro_combo.lineEdit()
        if editor is None:
            return

        def _on_text(text: str) -> None:
            if self._micro_search_updating:
                return
            self._micro_search_updating = True
            try:
                self._refresh_micro_combo(text)
            finally:
                self._micro_search_updating = False

        editor.textEdited.connect(_on_text)

    def _refresh_micro_combo(self, text: str) -> None:
        query = text.strip()
        current_data = self.micro_combo.currentData()
        if query:
            microbes = self.reference_service.search_microorganisms(query, limit=50)
        else:
            microbes = self.reference_service.list_microorganisms()
        with QSignalBlocker(self.micro_combo):
            self.micro_combo.clear()
            self.micro_combo.addItem("Выбрать", None)
            for m in microbes:
                label = f"{m.code or '-'} - {m.name}"
                self.micro_combo.addItem(label, m.id)
            if current_data is not None:
                idx = self.micro_combo.findData(current_data)
                if idx >= 0:
                    self.micro_combo.setCurrentIndex(idx)
            self.micro_combo.setEditText(text)

    def _setup_abx_rows(self) -> None:
        self._abx_list = self.reference_service.list_antibiotics()
        for row in range(self.susc_table.rowCount()):
            combo = self._create_abx_combo()
            self.susc_table.setCellWidget(row, 0, combo)
            connect_combo_resize_on_first_row(self.susc_table, combo, row)
        resize_columns_by_first_row(self.susc_table)

    def _setup_phage_rows(self) -> None:
        self._phage_list = self.reference_service.list_phages()
        for row in range(self.phage_table.rowCount()):
            combo = self._create_phage_combo()
            self.phage_table.setCellWidget(row, 0, combo)
            connect_combo_resize_on_first_row(self.phage_table, combo, row)
        resize_columns_by_first_row(self.phage_table)

    def _refresh_abx_combos(self, selected_ids: list[int | None]) -> None:
        self._abx_list = self.reference_service.list_antibiotics()
        for row in range(self.susc_table.rowCount()):
            combo = self._create_abx_combo()
            if row < len(selected_ids) and selected_ids[row] is not None:
                idx = combo.findData(selected_ids[row])
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            self.susc_table.setCellWidget(row, 0, combo)
            connect_combo_resize_on_first_row(self.susc_table, combo, row)
        resize_columns_by_first_row(self.susc_table)

    def _refresh_phage_combos(self, selected_ids: list[int | None]) -> None:
        self._phage_list = self.reference_service.list_phages()
        for row in range(self.phage_table.rowCount()):
            combo = self._create_phage_combo()
            if row < len(selected_ids) and selected_ids[row] is not None:
                idx = combo.findData(selected_ids[row])
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            self.phage_table.setCellWidget(row, 0, combo)
            connect_combo_resize_on_first_row(self.phage_table, combo, row)
        resize_columns_by_first_row(self.phage_table)

    def refresh_references(self) -> None:
        selected_material = self.material_type.currentData()
        selected_micro = self.micro_combo.currentData()
        abx_selected = [
            cast(QComboBox, combo_widget).currentData()
            if (combo_widget := self.susc_table.cellWidget(row, 0)) and isinstance(combo_widget, QComboBox)
            else None
            for row in range(self.susc_table.rowCount())
        ]
        phage_selected = [
            cast(QComboBox, combo_widget).currentData()
            if (combo_widget := self.phage_table.cellWidget(row, 0)) and isinstance(combo_widget, QComboBox)
            else None
            for row in range(self.phage_table.rowCount())
        ]

        self._load_material_types()
        if selected_material is not None:
            idx = self.material_type.findData(selected_material)
            if idx >= 0:
                self.material_type.setCurrentIndex(idx)

        self._load_microbes()
        if selected_micro is not None:
            idx = self.micro_combo.findData(selected_micro)
            if idx >= 0:
                self.micro_combo.setCurrentIndex(idx)

        self._refresh_abx_combos(abx_selected)
        self._refresh_phage_combos(phage_selected)

    def _create_abx_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItem("Выбрать", None)
        for abx in self._abx_list:
            combo.addItem(f"{abx.code} - {abx.name}", abx.id)
        return combo

    def _create_phage_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItem("Выбрать", None)
        for ph in self._phage_list:
            combo.addItem(f"{ph.code or '-'} - {ph.name}", ph.id)
        return combo

    def _add_susc_row(self) -> None:
        row = self.susc_table.rowCount()
        self.susc_table.insertRow(row)
        combo = self._create_abx_combo()
        self.susc_table.setCellWidget(row, 0, combo)
        connect_combo_resize_on_first_row(self.susc_table, combo, row)

    def _add_phage_row(self) -> None:
        row = self.phage_table.rowCount()
        self.phage_table.insertRow(row)
        combo = self._create_phage_combo()
        self.phage_table.setCellWidget(row, 0, combo)
        connect_combo_resize_on_first_row(self.phage_table, combo, row)

    def _delete_table_row(self, table: QTableWidget) -> None:
        if table.rowCount() <= 1:
            return
        row = table.currentRow()
        if row < 0:
            row = table.rowCount() - 1
        table.removeRow(row)

    def _make_table(self, headers, rows) -> QTableWidget:
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
        return table

    def _increase_table_height(self, table: QTableWidget, multiplier: float = 0.8) -> None:
        base = max(table.sizeHint().height(), 220)
        table.setMinimumHeight(int(base * multiplier))

    def _apply_default_templates(self) -> None:
        for row in range(self.susc_table.rowCount()):
            combo_widget = self.susc_table.cellWidget(row, 0)
            combo = cast(QComboBox, combo_widget) if isinstance(combo_widget, QComboBox) else None
            if combo and combo.currentData() is not None:
                ris_item = self.susc_table.item(row, 1)
                if not ris_item or not ris_item.text().strip():
                    self.susc_table.setItem(row, 1, QTableWidgetItem("S"))
                method_item = self.susc_table.item(row, 3)
                if not method_item or not method_item.text().strip():
                    self.susc_table.setItem(row, 3, QTableWidgetItem("disk"))

        for row in range(self.phage_table.rowCount()):
            combo_widget = self.phage_table.cellWidget(row, 0)
            combo = cast(QComboBox, combo_widget) if isinstance(combo_widget, QComboBox) else None
            free_item = self.phage_table.item(row, 1)
            has_phage = bool(combo and combo.currentData() is not None) or bool(
                free_item and free_item.text().strip()
            )
            if not has_phage:
                continue
            dia_item = self.phage_table.item(row, 2)
            if not dia_item or not dia_item.text().strip():
                self.phage_table.setItem(row, 2, QTableWidgetItem("0"))

        resize_columns_by_first_row(self.susc_table)
        resize_columns_by_first_row(self.phage_table)

    def _load_existing(self) -> None:
        try:
            if self.sample_id is None:
                return
            sample_id = cast(int, self.sample_id)
            detail = self.lab_service.get_detail(sample_id)
            sample = detail["sample"]
            self.material_type.setCurrentIndex(self.material_type.findData(sample.material_type_id))
            self.material_location.setText(sample.material_location or "")
            self.medium.setText(sample.medium or "")
            if sample.study_kind:
                idx_kind = self.study_kind.findData(sample.study_kind)
                if idx_kind >= 0:
                    self.study_kind.setCurrentIndex(idx_kind)
            if sample.ordered_at:
                self.ordered_at.setDateTime(sample.ordered_at)
            if sample.taken_at:
                self.taken_at.setDateTime(sample.taken_at)
            if sample.delivered_at:
                self.delivered_at.setDateTime(sample.delivered_at)
            if sample.growth_result_at:
                self.growth_result_at.setDateTime(sample.growth_result_at)
            if sample.growth_flag is None:
                self.growth_flag.setCurrentIndex(0)
            else:
                idx = self.growth_flag.findData(sample.growth_flag)
                if idx >= 0:
                    self.growth_flag.setCurrentIndex(idx)
            self.colony_desc.setText(sample.colony_desc or "")
            self.microscopy.setText(sample.microscopy or "")
            self.cfu.setText(sample.cfu or "")
            if sample.qc_due_at:
                self.qc_due_at.setText(sample.qc_due_at.strftime("%d.%m.%Y %H:%M"))
            if sample.qc_status:
                idx = self.qc_status.findData(sample.qc_status)
                if idx >= 0:
                    self.qc_status.setCurrentIndex(idx)
            iso = detail["isolation"]
            if iso:
                idx = self.micro_combo.findData(iso[0].microorganism_id)
                if idx >= 0:
                    self.micro_combo.setCurrentIndex(idx)
                self.micro_free.setText(iso[0].microorganism_free or "")
            self._fill_susceptibility(detail["susceptibility"])
            self._fill_phages(detail["phages"])
        except Exception as exc:  # noqa: BLE001
            set_status(self.error_label, str(exc), "error")

    def _collect_susceptibility(self) -> list[dict]:
        rows: list[SusceptibilityInput] = []
        for row in range(self.susc_table.rowCount()):
            abx_widget = self.susc_table.cellWidget(row, 0)
            abx_combo = cast(QComboBox, abx_widget) if isinstance(abx_widget, QComboBox) else None
            ris_item = self.susc_table.item(row, 1)
            mic_item = self.susc_table.item(row, 2)
            method_item = self.susc_table.item(row, 3)
            rows.append(
                SusceptibilityInput(
                    row_number=row + 1,
                    antibiotic_id=abx_combo.currentData() if abx_combo else None,
                    ris=ris_item.text() if ris_item else None,
                    mic_text=mic_item.text() if mic_item else None,
                    method=method_item.text() if method_item else None,
                )
            )
        return build_susceptibility_payload(rows)

    def _collect_phages(self) -> list[dict]:
        rows: list[PhageInput] = []
        for row in range(self.phage_table.rowCount()):
            ph_widget = self.phage_table.cellWidget(row, 0)
            ph_combo = cast(QComboBox, ph_widget) if isinstance(ph_widget, QComboBox) else None
            free_item = self.phage_table.item(row, 1)
            dia_item = self.phage_table.item(row, 2)
            rows.append(
                PhageInput(
                    row_number=row + 1,
                    phage_id=ph_combo.currentData() if ph_combo else None,
                    phage_free=free_item.text() if free_item else "",
                    diameter_text=dia_item.text() if dia_item else None,
                )
            )
        return build_phage_payload(rows)

    def _has_result_data(self) -> bool:
        susceptibility_rows: list[SusceptibilityInput] = []
        for row in range(self.susc_table.rowCount()):
            abx_widget = self.susc_table.cellWidget(row, 0)
            abx_combo = cast(QComboBox, abx_widget) if isinstance(abx_widget, QComboBox) else None
            ris_item = self.susc_table.item(row, 1)
            mic_item = self.susc_table.item(row, 2)
            method_item = self.susc_table.item(row, 3)
            susceptibility_rows.append(
                SusceptibilityInput(
                    row_number=row + 1,
                    antibiotic_id=abx_combo.currentData() if abx_combo else None,
                    ris=ris_item.text() if ris_item else None,
                    mic_text=mic_item.text() if mic_item else None,
                    method=method_item.text() if method_item else None,
                )
            )
        phage_rows: list[PhageInput] = []
        for row in range(self.phage_table.rowCount()):
            ph_widget = self.phage_table.cellWidget(row, 0)
            ph_combo = cast(QComboBox, ph_widget) if isinstance(ph_widget, QComboBox) else None
            free_item = self.phage_table.item(row, 1)
            dia_item = self.phage_table.item(row, 2)
            phage_rows.append(
                PhageInput(
                    row_number=row + 1,
                    phage_id=ph_combo.currentData() if ph_combo else None,
                    phage_free=free_item.text() if free_item else "",
                    diameter_text=dia_item.text() if dia_item else None,
                )
            )
        return has_lab_result_data(
            growth_flag=self.growth_flag.currentData(),
            colony_desc=self.colony_desc.text(),
            microscopy=self.microscopy.text(),
            cfu=self.cfu.text(),
            microorganism_id=self.micro_combo.currentData(),
            microorganism_free=self.micro_free.text(),
            susceptibility_rows=susceptibility_rows,
            phage_rows=phage_rows,
        )

    def _build_result_update(self) -> LabSampleResultUpdate:
        has_results = self._has_result_data()
        susceptibility = self._collect_susceptibility() if has_results else []
        phages = self._collect_phages() if has_results else []
        growth_result_at = None
        if has_results and self.growth_result_at.dateTime().isValid():
            growth_result_at = cast(datetime | None, self.growth_result_at.dateTime().toPython())
        return compose_lab_result_update(
            has_results=has_results,
            growth_flag=self.growth_flag.currentData(),
            growth_result_at=growth_result_at,
            colony_desc=self.colony_desc.text(),
            microscopy=self.microscopy.text(),
            cfu=self.cfu.text(),
            qc_status=self.qc_status.currentData(),
            microorganism_id=self.micro_combo.currentData(),
            microorganism_free=self.micro_free.text(),
            susceptibility=susceptibility,
            phages=phages,
        )

    def on_save(self) -> None:
        clear_status(self.error_label)
        if self.sample_id is None:
            try:
                material_id = self.material_type.currentData()
                if material_id is None:
                    raise ValueError("Выберите тип материала")
                qc_status = self.qc_status.currentData()
                req = LabSampleCreateRequest(
                    patient_id=self.patient_id,
                    emr_case_id=self.emr_case_id,
                    material_type_id=material_id,
                    material_location=self.material_location.text().strip() or None,
                    medium=self.medium.text().strip() or None,
                    study_kind=self.study_kind.currentData(),
                    ordered_at=cast(datetime | None, self.ordered_at.dateTime().toPython())
                    if self.ordered_at.dateTime().isValid()
                    else None,
                    taken_at=cast(datetime | None, self.taken_at.dateTime().toPython())
                    if self.taken_at.dateTime().isValid()
                    else None,
                    delivered_at=cast(datetime | None, self.delivered_at.dateTime().toPython())
                    if self.delivered_at.dateTime().isValid()
                    else None,
                    created_by=None,
                )
                resp = self.lab_service.create_sample(req)
                self.sample_id = resp.id
                if resp.qc_due_at:
                    self.qc_due_at.setText(resp.qc_due_at.strftime("%d.%m.%Y %H:%M"))
                needs_update = self._has_result_data() or (qc_status and qc_status != "valid")
                if needs_update:
                    upd = self._build_result_update()
                    self.lab_service.update_result(self.sample_id, upd, actor_id=None)
                self.accept()
            except Exception as exc:  # noqa: BLE001
                set_status(self.error_label, str(exc), "error")
        else:
            try:
                material_id = self.material_type.currentData()
                if material_id is None:
                    raise ValueError("Выберите тип материала")
                upd_sample = LabSampleUpdateRequest(
                    material_type_id=material_id,
                    material_location=self.material_location.text().strip() or None,
                    medium=self.medium.text().strip() or None,
                    study_kind=self.study_kind.currentData(),
                    ordered_at=cast(datetime | None, self.ordered_at.dateTime().toPython())
                    if self.ordered_at.dateTime().isValid()
                    else None,
                    taken_at=cast(datetime | None, self.taken_at.dateTime().toPython())
                    if self.taken_at.dateTime().isValid()
                    else None,
                    delivered_at=cast(datetime | None, self.delivered_at.dateTime().toPython())
                    if self.delivered_at.dateTime().isValid()
                    else None,
                )
                self.lab_service.update_sample(self.sample_id, upd_sample, actor_id=None)
                upd = self._build_result_update()
                self.lab_service.update_result(self.sample_id, upd, actor_id=None)
                self.accept()
            except Exception as exc:  # noqa: BLE001
                set_status(self.error_label, str(exc), "error")

    def _fill_susceptibility(self, rows) -> None:
        self.susc_table.clearContents()
        self.susc_table.setRowCount(max(len(rows), self.susc_table.rowCount()))
        self._setup_abx_rows()
        for idx, r in enumerate(rows):
            combo_widget = self.susc_table.cellWidget(idx, 0)
            combo = cast(QComboBox, combo_widget) if isinstance(combo_widget, QComboBox) else None
            if combo:
                combo.setCurrentIndex(combo.findData(r.antibiotic_id))
            self.susc_table.setItem(idx, 1, QTableWidgetItem(r.ris or ""))
            self.susc_table.setItem(idx, 2, QTableWidgetItem(str(r.mic_mg_l) if r.mic_mg_l is not None else ""))
            self.susc_table.setItem(idx, 3, QTableWidgetItem(r.method or ""))
        resize_columns_by_first_row(self.susc_table)

    def _fill_phages(self, rows) -> None:
        self.phage_table.clearContents()
        self.phage_table.setRowCount(max(len(rows), self.phage_table.rowCount()))
        self._setup_phage_rows()
        for idx, r in enumerate(rows):
            combo_widget = self.phage_table.cellWidget(idx, 0)
            combo = cast(QComboBox, combo_widget) if isinstance(combo_widget, QComboBox) else None
            if combo:
                combo.setCurrentIndex(combo.findData(r.phage_id))
            self.phage_table.setItem(idx, 1, QTableWidgetItem(r.phage_free or ""))
            self.phage_table.setItem(idx, 2, QTableWidgetItem(str(r.lysis_diameter_mm) if r.lysis_diameter_mm is not None else ""))
        resize_columns_by_first_row(self.phage_table)
