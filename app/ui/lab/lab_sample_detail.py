from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.lab_dto import LabSampleResultUpdate
from app.application.services.lab_sample_payload_service import (
    PhageInput,
    SusceptibilityInput,
    build_lab_sample_create_request,
    build_lab_sample_update_request,
    build_phage_payload,
    build_susceptibility_payload,
    compose_lab_result_update,
    has_lab_result_data,
)
from app.application.services.lab_service import LabService
from app.application.services.reference_service import ReferenceService
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.datetime_inputs import (
    create_optional_datetime_edit,
    optional_datetime_value,
)
from app.ui.widgets.dialog_utils import localize_button_box
from app.ui.widgets.notifications import clear_status, set_status
from app.ui.widgets.sample_header import SampleHeader
from app.ui.widgets.susceptibility_panel import SusceptibilityPanel
from app.ui.widgets.table_utils import connect_combo_autowidth


class LabSampleDetailDialog(QDialog):
    def __init__(
        self,
        lab_service: LabService,
        reference_service: ReferenceService,
        patient_id: int,
        emr_case_id: int | None,
        actor_id: int | None,
        sample_id: int | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.lab_service = lab_service
        self.reference_service = reference_service
        self.patient_id = patient_id
        self.emr_case_id = emr_case_id
        self.actor_id = actor_id
        self.sample_id: int | None = sample_id
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
        self.resize(1100, 820)
        self.setMinimumSize(900, 640)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.sample_header = SampleHeader(self)
        self.sample_header.set_lab_context(
            self.sample_id,
            "",
            f"Пациент ID {self.patient_id}",
        )
        layout.addWidget(self.sample_header)

        self._build_fields()

        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("sampleTabs")
        self.tabs.addTab(self._make_tab_scroll(self._build_sample_tab()), "Проба")
        self.tabs.addTab(self._make_tab_scroll(self._build_identification_tab()), "Идентификация")
        self.tabs.addTab(self._make_tab_scroll(self._build_susceptibility_tab()), "Чувствительность")
        self.tabs.addTab(self._make_tab_scroll(self._build_qc_tab()), "Контроль качества")
        layout.addWidget(self.tabs, 1)

        self.error_label = QLabel()
        set_status(self.error_label, "", "info")
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.setObjectName("sampleFooter")
        localize_button_box(buttons)
        template_btn = buttons.addButton("Заполнить шаблоны", QDialogButtonBox.ButtonRole.ActionRole)
        compact_button(template_btn)
        template_btn.clicked.connect(self._apply_default_templates)
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_btn:
            save_btn.setText("Сохранить")
            save_btn.setObjectName("primaryButton")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("Отмена")
        buttons.accepted.connect(self.on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_material_types()
        self._load_microbes()
        self._setup_validation_hooks()
        if self.sample_id:
            self._load_existing()

    def _build_fields(self) -> None:
        self.material_type = QComboBox()
        self.material_type.setEditable(False)
        self.material_type.addItem("Выбрать", None)
        self.taken_at = create_optional_datetime_edit()
        self.ordered_at = create_optional_datetime_edit()
        self.delivered_at = create_optional_datetime_edit()
        self.study_kind = QComboBox()
        self.study_kind.addItem("Выбрать", None)
        self.study_kind.addItem("Первичное", "primary")
        self.study_kind.addItem("Повторное", "repeat")
        self.material_location = QLineEdit()
        self.medium = QLineEdit()

        self.growth_flag = QComboBox()
        self.growth_flag.addItem("Выбрать", None)
        self.growth_flag.addItem("Нет", 0)
        self.growth_flag.addItem("Да", 1)
        self.growth_result_at = create_optional_datetime_edit()
        self.colony_desc = QLineEdit()
        self.microscopy = QLineEdit()
        self.cfu = QLineEdit()

        self.qc_status = QComboBox()
        self.qc_status.addItem("Выберите статус QC", None)
        self.qc_status.addItem("Допустимо", "valid")
        self.qc_status.addItem("Условно", "conditional")
        self.qc_status.addItem("Брак", "rejected")
        self.qc_status.setItemData(0, 0, Qt.ItemDataRole.UserRole - 1)
        self.qc_due_at = QLabel("-")
        self.qc_due_at.setObjectName("muted")

        self.micro_combo = QComboBox()
        self.micro_combo.setEditable(True)
        self.micro_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.micro_combo.addItem("Выбрать", None)
        self.micro_free = QLineEdit()
        self.micro_free.setPlaceholderText("если нет в справочнике")

        self.susceptibility_panel = SusceptibilityPanel(
            antibiotics_service=self.reference_service,
            phages_service=self.reference_service,
            parent=self,
        )
        self.susc_table = self.susceptibility_panel.susc_table
        self.phage_table = self.susceptibility_panel.phage_table

    def _build_sample_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)

        main_frame, main_layout = self._make_section("Основные данные")
        main_grid = QGridLayout()
        main_grid.setHorizontalSpacing(12)
        main_grid.setVerticalSpacing(8)
        self._add_grid_field(main_grid, 0, 0, "Тип материала", self.material_type)
        self._add_grid_field(main_grid, 0, 1, "Время взятия", self.taken_at)
        self._add_grid_field(main_grid, 1, 0, "Среда", self.medium)
        self._add_grid_field(main_grid, 1, 1, "Дата доставки", self.delivered_at)
        self._add_grid_field(main_grid, 2, 0, "Тип исследования", self.study_kind)
        self._add_grid_field(main_grid, 2, 1, "Место забора", self.material_location)
        self._add_grid_field(main_grid, 3, 0, "Дата назначения", self.ordered_at)
        main_grid.setColumnStretch(1, 1)
        main_grid.setColumnStretch(3, 1)
        main_layout.addLayout(main_grid)
        layout.addWidget(main_frame)

        result_frame, result_layout = self._make_section("Результаты роста")
        result_grid = QGridLayout()
        result_grid.setHorizontalSpacing(12)
        result_grid.setVerticalSpacing(8)
        self._add_grid_field(result_grid, 0, 0, "Рост", self.growth_flag)
        self._add_grid_field(result_grid, 0, 1, "Результат от", self.growth_result_at)
        self._add_grid_field(result_grid, 1, 0, "Колонии/морфология", self.colony_desc)
        self._add_grid_field(result_grid, 1, 1, "КОЕ", self.cfu)
        self._add_grid_field(result_grid, 2, 0, "Микроскопия", self.microscopy)
        result_grid.setColumnStretch(1, 1)
        result_grid.setColumnStretch(3, 1)
        result_layout.addLayout(result_grid)
        layout.addWidget(result_frame)
        layout.addStretch(1)
        return content

    def _build_identification_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)

        frame, frame_layout = self._make_section("Идентификация")
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        self._add_grid_field(grid, 0, 0, "Микроорганизм", self.micro_combo)
        self._add_grid_field(grid, 0, 1, "Микроорганизм (свободно)", self.micro_free)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        frame_layout.addLayout(grid)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)
        for text in ("E. coli", "S. aureus"):
            btn = QPushButton(text)
            compact_button(btn)
            btn.clicked.connect(lambda _checked=False, value=text: self._apply_micro_template(value))
            quick_row.addWidget(btn)
        quick_row.addStretch()
        frame_layout.addLayout(quick_row)

        layout.addWidget(frame)
        layout.addStretch(1)
        return content

    def _build_susceptibility_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)

        frame, frame_layout = self._make_section("Чувствительность и фаги")
        frame_layout.addWidget(self.susceptibility_panel)
        layout.addWidget(frame)
        layout.addStretch(1)
        return content

    def _build_qc_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)

        frame, frame_layout = self._make_section("Контроль качества")
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        self._add_grid_field(grid, 0, 0, "Статус QC", self.qc_status)
        self._add_grid_field(grid, 0, 1, "Срок QC", self.qc_due_at)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        frame_layout.addLayout(grid)
        layout.addWidget(frame)
        layout.addStretch(1)
        return content

    def _make_tab_scroll(self, content: QWidget) -> QScrollArea:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        return scroll

    def _make_section(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame(self)
        frame.setObjectName("sampleSection")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)
        return frame, layout

    def _add_grid_field(
        self,
        grid: QGridLayout,
        row: int,
        column: int,
        label_text: str,
        widget: QWidget,
    ) -> None:
        label = QLabel(label_text)
        label.setObjectName("sampleFieldLabel")
        label.setBuddy(widget)
        grid.addWidget(label, row, column * 2)
        grid.addWidget(widget, row, column * 2 + 1)

    def _setup_validation_hooks(self) -> None:
        self.material_type.currentIndexChanged.connect(lambda: self._clear_widget_error(self.material_type))
        self.taken_at.dateTimeChanged.connect(lambda: self._clear_widget_error(self.taken_at))

    def _set_widget_error(self, widget: QWidget, message: str | None) -> None:
        widget.setProperty("error", bool(message))
        widget.setToolTip(message or "")
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _clear_widget_error(self, widget: QWidget) -> None:
        if widget.property("error"):
            self._set_widget_error(widget, None)

    def _clear_validation_errors(self) -> None:
        for widget in (self.material_type, self.taken_at):
            self._set_widget_error(widget, None)

    def _validate_required_fields(self) -> bool:
        self._clear_validation_errors()
        missing = False
        if self.material_type.currentData() is None:
            self._set_widget_error(self.material_type, "Обязательное поле: тип материала")
            missing = True
        if self._to_python_datetime(self.taken_at) is None:
            self._set_widget_error(self.taken_at, "Обязательное поле: время взятия")
            missing = True
        if missing:
            set_status(
                self.error_label,
                "Заполните обязательные поля, подсвеченные красным.",
                "error",
            )
        return not missing

    def _apply_micro_template(self, text: str) -> None:
        query = text.lower()
        for index in range(self.micro_combo.count()):
            if query in self.micro_combo.itemText(index).lower():
                self.micro_combo.setCurrentIndex(index)
                return
        self.micro_free.setText(text)

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
            for microbe in microbes:
                label = f"{microbe.code or '-'} - {microbe.name}"
                self.micro_combo.addItem(label, microbe.id)
            if current_data is not None:
                idx = self.micro_combo.findData(current_data)
                if idx >= 0:
                    self.micro_combo.setCurrentIndex(idx)
            self.micro_combo.setEditText(text)

    def refresh_references(self) -> None:
        selected_material = self.material_type.currentData()
        selected_micro = self.micro_combo.currentData()

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

        self.susceptibility_panel.refresh_references()

    def _setup_abx_rows(self) -> None:
        self.susceptibility_panel._setup_abx_rows()

    def _setup_phage_rows(self) -> None:
        self.susceptibility_panel._setup_phage_rows()

    def _refresh_abx_combos(self, selected_ids: list[int | None]) -> None:
        self.susceptibility_panel._refresh_abx_combos(selected_ids)

    def _refresh_phage_combos(self, selected_ids: list[int | None]) -> None:
        self.susceptibility_panel._refresh_phage_combos(selected_ids)

    def _add_susc_row(self) -> None:
        self.susceptibility_panel._add_susc_row()

    def _add_phage_row(self) -> None:
        self.susceptibility_panel._add_phage_row()

    def _delete_table_row(self, table: QTableWidget) -> None:
        self.susceptibility_panel._delete_table_row(table)

    def _apply_default_templates(self) -> None:
        self.susceptibility_panel.apply_default_templates()

    def _load_existing(self) -> None:
        try:
            if self.sample_id is None:
                return
            sample_id = cast(int, self.sample_id)
            detail = self.lab_service.get_detail(sample_id)
            sample = detail["sample"]
            self.sample_header.set_lab_context(
                getattr(sample, "id", sample_id),
                getattr(sample, "lab_no", "") or "",
                f"Пациент ID {self.patient_id}",
            )
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
            isolation = detail["isolation"]
            if isolation:
                idx = self.micro_combo.findData(isolation[0].microorganism_id)
                if idx >= 0:
                    self.micro_combo.setCurrentIndex(idx)
                self.micro_free.setText(isolation[0].microorganism_free or "")
            self.susceptibility_panel.set_data(detail["susceptibility"], detail["phages"])
        except Exception as exc:  # noqa: BLE001
            set_status(self.error_label, str(exc), "error")

    def _collect_susceptibility_inputs(self) -> list[SusceptibilityInput]:
        return [
            SusceptibilityInput(
                row_number=row.row_number,
                antibiotic_id=row.antibiotic_id,
                ris=row.ris,
                mic_text=row.mic_text,
                method=row.method,
            )
            for row in self.susceptibility_panel.get_susceptibility_rows()
        ]

    def _collect_phage_inputs(self) -> list[PhageInput]:
        return [
            PhageInput(
                row_number=row.row_number,
                phage_id=row.phage_id,
                phage_free=row.phage_free,
                diameter_text=row.diameter_text,
            )
            for row in self.susceptibility_panel.get_phage_rows()
        ]

    def _collect_susceptibility(self) -> list[dict]:
        return build_susceptibility_payload(self._collect_susceptibility_inputs())

    def _collect_phages(self) -> list[dict]:
        return build_phage_payload(self._collect_phage_inputs())

    def _has_result_data(self) -> bool:
        return has_lab_result_data(
            growth_flag=self.growth_flag.currentData(),
            colony_desc=self.colony_desc.text(),
            microscopy=self.microscopy.text(),
            cfu=self.cfu.text(),
            microorganism_id=self.micro_combo.currentData(),
            microorganism_free=self.micro_free.text(),
            susceptibility_rows=self._collect_susceptibility_inputs(),
            phage_rows=self._collect_phage_inputs(),
        )

    def _build_result_update(self) -> LabSampleResultUpdate:
        has_results = self._has_result_data()
        susceptibility = self._collect_susceptibility() if has_results else []
        phages = self._collect_phages() if has_results else []
        growth_result_at = self._to_python_datetime(self.growth_result_at) if has_results else None
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

    @staticmethod
    def _to_python_datetime(widget: QDateTimeEdit) -> datetime | None:
        return optional_datetime_value(widget)

    def on_save(self) -> None:
        clear_status(self.error_label)
        if self.actor_id is None:
            set_status(self.error_label, "Не удалось определить пользователя сессии", "error")
            return
        if not self._validate_required_fields():
            return
        if self.sample_id is None:
            try:
                material_id = self.material_type.currentData()
                qc_status = self.qc_status.currentData()
                req = build_lab_sample_create_request(
                    patient_id=self.patient_id,
                    emr_case_id=self.emr_case_id,
                    material_type_id=material_id,
                    material_location=self.material_location.text(),
                    medium=self.medium.text(),
                    study_kind=self.study_kind.currentData(),
                    ordered_at=self._to_python_datetime(self.ordered_at),
                    taken_at=self._to_python_datetime(self.taken_at),
                    delivered_at=self._to_python_datetime(self.delivered_at),
                    created_by=None,
                )
                resp = self.lab_service.create_sample(req, actor_id=self.actor_id)
                self.sample_id = resp.id
                self.sample_header.set_lab_context(
                    self.sample_id,
                    getattr(resp, "lab_no", "") or "",
                    f"Пациент ID {self.patient_id}",
                )
                if resp.qc_due_at:
                    self.qc_due_at.setText(resp.qc_due_at.strftime("%d.%m.%Y %H:%M"))
                needs_update = self._has_result_data() or (qc_status and qc_status != "valid")
                if needs_update:
                    upd = self._build_result_update()
                    self.lab_service.update_result(self.sample_id, upd, actor_id=self.actor_id)
                self.accept()
            except Exception as exc:  # noqa: BLE001
                set_status(self.error_label, str(exc), "error")
        else:
            try:
                material_id = self.material_type.currentData()
                upd_sample = build_lab_sample_update_request(
                    material_type_id=material_id,
                    material_location=self.material_location.text(),
                    medium=self.medium.text(),
                    study_kind=self.study_kind.currentData(),
                    ordered_at=self._to_python_datetime(self.ordered_at),
                    taken_at=self._to_python_datetime(self.taken_at),
                    delivered_at=self._to_python_datetime(self.delivered_at),
                )
                self.lab_service.update_sample(self.sample_id, upd_sample, actor_id=self.actor_id)
                upd = self._build_result_update()
                self.lab_service.update_result(self.sample_id, upd, actor_id=self.actor_id)
                self.accept()
            except Exception as exc:  # noqa: BLE001
                set_status(self.error_label, str(exc), "error")

    def _fill_susceptibility(self, rows: list[Any]) -> None:
        self.susceptibility_panel.set_susceptibility_rows(rows)

    def _fill_phages(self, rows: list[Any]) -> None:
        self.susceptibility_panel.set_phage_rows(rows)
