from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, cast

from PySide6.QtCore import QDate, QDateTime, QSignalBlocker, Qt, QTime, Signal
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
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.sanitary_dto import (
    SanitarySampleCreateRequest,
    SanitarySampleResultUpdate,
    SanitarySampleUpdateRequest,
)
from app.application.services.reference_service import ReferenceService
from app.application.services.sanitary_service import SanitaryService
from app.ui.sanitary.history_view_helpers import (
    build_meta_line,
    filter_and_sort_samples,
    growth_visuals,
    paginate_samples,
    resolve_micro_text,
    summarize_history,
)
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import clear_status, set_status
from app.ui.widgets.responsive_actions import ResponsiveActionsPanel
from app.ui.widgets.table_utils import (
    connect_combo_autowidth,
    connect_combo_resize_on_first_row,
    resize_columns_by_first_row,
)


class SanitaryHistoryDialog(QDialog):
    references_updated = Signal()
    _micro_search_updating: bool = False

    def __init__(
        self,
        sanitary_service: SanitaryService,
        reference_service: ReferenceService,
        department_id: int,
        department_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.sanitary_service = sanitary_service
        self.reference_service = reference_service
        self.department_id = department_id
        self.department_name = department_name
        self._microbe_map: dict[int, str] = {}
        self._micro_search_updating: bool = False
        self._date_empty = QDate(2000, 1, 1)
        self.page_index = 1
        self.page_size = 50
        self.setWindowTitle(f"Санитарные пробы - {department_name}")
        if parent is not None and hasattr(parent, "references_updated"):
            parent.references_updated.connect(self._on_references_updated)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        title = QLabel("История санитарных проб")
        title.setObjectName("sectionTitle")
        header_row.addWidget(title)
        header_row.addStretch()
        self.summary_label = QLabel("Проб: 0, положительных: 0, последняя: -")
        self.summary_label.setObjectName("muted")
        header_row.addWidget(self.summary_label)
        layout.addLayout(header_row)

        dept_label = QLabel(f"Отделение: {self.department_name or self.department_id}")
        dept_label.setObjectName("homeUserInfo")
        layout.addWidget(dept_label)

        filter_box = QGroupBox("Фильтры")
        filter_row = QHBoxLayout(filter_box)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по номеру пробы")
        self.search_input.textChanged.connect(self._on_filter_changed)
        self.growth_filter = QComboBox()
        self.growth_filter.addItem("Выбрать", None)
        self.growth_filter.addItem("Положительные", 1)
        self.growth_filter.addItem("Отрицательные", 0)
        connect_combo_autowidth(self.growth_filter)
        self.growth_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.date_from = QDateTimeEdit(calendarPopup=True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setMinimumDate(self._date_empty)
        self.date_from.setSpecialValueText("")
        self.date_from.setDate(self._date_empty)
        self.date_from.dateChanged.connect(self._on_filter_changed)
        self.date_to = QDateTimeEdit(calendarPopup=True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setMinimumDate(self._date_empty)
        self.date_to.setSpecialValueText("")
        self.date_to.setDate(self._date_empty)
        self.date_to.dateChanged.connect(self._on_filter_changed)
        clear_filters_btn = QPushButton("Сбросить")
        compact_button(clear_filters_btn)
        clear_filters_btn.clicked.connect(self._clear_filters)
        filter_row.addWidget(QLabel("Номер пробы"))
        filter_row.addWidget(self.search_input)
        filter_row.addWidget(QLabel("Рост"))
        filter_row.addWidget(self.growth_filter)
        filter_row.addWidget(QLabel("Дата от"))
        filter_row.addWidget(self.date_from)
        filter_row.addWidget(QLabel("Дата до"))
        filter_row.addWidget(self.date_to)
        filter_row.addWidget(clear_filters_btn)
        filter_row.addStretch()
        layout.addWidget(filter_box)

        list_box = QGroupBox("История проб")
        list_layout = QVBoxLayout(list_box)
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        self.list_widget.itemDoubleClicked.connect(self._edit_selected)
        list_layout.addWidget(self.list_widget)
        paging_row = QHBoxLayout()
        self.page_label = QLabel("Стр. 1 / 1")
        self.prev_btn = QPushButton("Назад")
        compact_button(self.prev_btn)
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn = QPushButton("Вперёд")
        compact_button(self.next_btn)
        self.next_btn.clicked.connect(self._next_page)
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["20", "50", "100"])
        self.page_size_combo.setCurrentText(str(self.page_size))
        self.page_size_combo.currentIndexChanged.connect(self._on_page_size_changed)
        paging_row.addWidget(QLabel("На странице"))
        paging_row.addWidget(self.page_size_combo)
        paging_row.addStretch()
        paging_row.addWidget(self.prev_btn)
        paging_row.addWidget(self.next_btn)
        paging_row.addWidget(self.page_label)
        list_layout.addLayout(paging_row)
        layout.addWidget(list_box)

        actions_box = QGroupBox("Действия")
        actions_layout = QVBoxLayout(actions_box)
        new_btn = QPushButton("Новая проба")
        compact_button(new_btn)
        new_btn.clicked.connect(self._open_new_dialog)
        refresh_btn = QPushButton("Обновить")
        compact_button(refresh_btn)
        refresh_btn.clicked.connect(self.refresh)
        self._actions_panel = ResponsiveActionsPanel(min_button_width=124, max_columns=2)
        self._actions_panel.set_buttons([new_btn, refresh_btn])
        self._actions_panel.set_compact(self.width() < 1300)
        actions_layout.addWidget(self._actions_panel)
        layout.addWidget(actions_box)

        self.refresh()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_actions_panel"):
            self._actions_panel.set_compact(self.width() < 1300)

    def refresh(self) -> None:
        self.list_widget.clear()
        self._load_microbe_map()
        search = self.search_input.text().strip().lower()
        growth = self.growth_filter.currentData()
        date_from = self._date_value(self.date_from)
        date_to = self._date_value(self.date_to)
        filtered = filter_and_sort_samples(
            self.sanitary_service.list_samples_by_department(self.department_id),
            search=search,
            growth=growth,
            date_from=date_from,
            date_to=date_to,
        )
        page_state = paginate_samples(
            filtered,
            page_index=self.page_index,
            page_size=self.page_size,
        )
        self.page_index = page_state.page_index
        summary = summarize_history(filtered)
        self.summary_label.setText(
            f"Проб: {summary.total}, положительных: {summary.positives}, последняя: {summary.last_taken_text}"
        )
        if not page_state.page_items:
            self._add_empty_item("Проб пока нет.")
            self._update_paging(0, 0)
            return
        for sample in page_state.page_items:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, sample.id)
            card = self._build_sample_item(sample)
            item.setSizeHint(card.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, card)
        self._update_paging(summary.total, len(page_state.page_items))

    def _build_sample_item(self, sample) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("listCard")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        header = QHBoxLayout()
        header.setSpacing(6)
        status_dot = QLabel()
        status_dot.setObjectName("cardStatusDot")
        status_dot.setFixedSize(8, 8)
        _status_color, growth_text = growth_visuals(sample.growth_flag)
        status_tone = "unknown"
        if sample.growth_flag == 1:
            status_tone = "danger"
        elif sample.growth_flag == 0:
            status_tone = "ok"
        status_dot.setProperty("tone", status_tone)
        title = QLabel(f"{sample.lab_no} (id {sample.id})")
        title.setObjectName("cardTitle")
        header.addWidget(status_dot)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        micro_text = resolve_micro_text(sample, microbe_map=self._microbe_map)
        meta = QLabel(build_meta_line(sample, growth_text=growth_text, micro_text=micro_text))
        meta.setObjectName("cardMeta")
        layout.addWidget(meta)
        return wrapper

    def _add_empty_item(self, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.list_widget.addItem(item)

    def _on_filter_changed(self) -> None:
        self.page_index = 1
        self.refresh()

    def _clear_filters(self) -> None:
        self.search_input.clear()
        self.growth_filter.setCurrentIndex(0)
        self.date_from.setDate(self._date_empty)
        self.date_to.setDate(self._date_empty)
        self.page_index = 1
        self.refresh()

    def _on_page_size_changed(self) -> None:
        try:
            self.page_size = int(self.page_size_combo.currentText())
        except ValueError:
            self.page_size = 50
        self.page_index = 1
        self.refresh()

    def _prev_page(self) -> None:
        if self.page_index > 1:
            self.page_index -= 1
            self.refresh()

    def _next_page(self) -> None:
        self.page_index += 1
        self.refresh()

    def _update_paging(self, total: int, shown: int) -> None:
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        if self.page_index > total_pages:
            self.page_index = total_pages
        self.page_label.setText(f"Стр. {self.page_index} / {total_pages}")
        self.prev_btn.setEnabled(self.page_index > 1)
        self.next_btn.setEnabled(self.page_index < total_pages)
        if total == 0:
            self.page_label.setText("Стр. 1 / 1")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)

    def _date_value(self, widget: QDateTimeEdit) -> date | None:
        qdate = widget.date()
        if qdate == self._date_empty:
            return None
        return cast(date, qdate.toPython())

    def _load_microbe_map(self) -> None:
        self._microbe_map = {}
        for micro in self.reference_service.list_microorganisms():
            label = f"{micro.code or '-'} - {micro.name}"
            micro_id = cast(int, micro.id)
            self._microbe_map[micro_id] = label

    def _open_new_dialog(self) -> None:
        dlg = SanitarySampleDetailDialog(
            self.sanitary_service,
            self.reference_service,
            department_id=self.department_id,
            parent=self,
        )
        self.references_updated.connect(dlg.refresh_references)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
        self.references_updated.disconnect(dlg.refresh_references)

    def _edit_selected(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            return
        sample_id = item.data(Qt.ItemDataRole.UserRole)
        dlg = SanitarySampleDetailDialog(
            self.sanitary_service,
            self.reference_service,
            department_id=self.department_id,
            sample_id=sample_id,
            parent=self,
        )
        self.references_updated.connect(dlg.refresh_references)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
        self.references_updated.disconnect(dlg.refresh_references)

    def _on_references_updated(self) -> None:
        self.refresh()
        self.references_updated.emit()


class SanitarySampleDetailDialog(QDialog):
    def __init__(
        self,
        sanitary_service: SanitaryService,
        reference_service: ReferenceService,
        department_id: int,
        sample_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.sanitary_service = sanitary_service
        self.reference_service = reference_service
        self.department_id = department_id
        self.sample_id = sample_id
        self._abx_list: list[Any] = []
        self._phage_list: list[Any] = []
        self.setWindowTitle("Санитарная проба")
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

        title = QLabel("Карточка санитарной пробы")
        title.setObjectName("sectionTitle")
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(12)
        content_layout.addWidget(title)

        # Основные данные
        self.sampling_point = QLineEdit()
        self.room = QLineEdit()
        self.medium = QLineEdit()
        self.taken_at = QDateTimeEdit()
        self.delivered_at = QDateTimeEdit()
        min_dt = QDateTime(QDate(2024, 1, 1), QTime(0, 0))
        self.taken_at.setMinimumDateTime(min_dt)
        self.delivered_at.setMinimumDateTime(min_dt)
        self.taken_at.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.delivered_at.setDisplayFormat("dd.MM.yyyy HH:mm")

        main_box = QGroupBox("Основные данные")
        main_form = QFormLayout(main_box)
        main_form.addRow("Точка отбора", self.sampling_point)
        main_form.addRow("Помещение", self.room)
        main_form.addRow("Среда", self.medium)
        main_form.addRow("Время взятия", self.taken_at)
        main_form.addRow("Дата доставки", self.delivered_at)
        content_layout.addWidget(main_box)

        # Результаты роста
        self.growth_flag = QComboBox()
        self.growth_flag.addItem("Выбрать", None)
        self.growth_flag.addItem("Нет", 0)
        self.growth_flag.addItem("Да", 1)
        self.growth_result_at = QDateTimeEdit()
        self.growth_result_at.setMinimumDateTime(min_dt)
        self.growth_result_at.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.colony_desc = QLineEdit()
        self.microscopy = QLineEdit()
        self.cfu = QLineEdit()

        result_box = QGroupBox("Результаты роста")
        result_form = QFormLayout(result_box)
        result_form.addRow("Рост", self.growth_flag)
        result_form.addRow("Результат от", self.growth_result_at)
        result_form.addRow("Колонии/морфология", self.colony_desc)
        result_form.addRow("Микроскопия", self.microscopy)
        result_form.addRow("КОЕ", self.cfu)
        content_layout.addWidget(result_box)

        # Идентификация
        self.micro_combo = QComboBox()
        self.micro_combo.setEditable(True)
        self.micro_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.micro_combo.addItem("Выбрать", None)
        self.micro_free = QLineEdit()
        self.micro_free.setPlaceholderText("если нет в справочнике")

        micro_box = QGroupBox("Идентификация")
        micro_form = QFormLayout(micro_box)
        micro_form.addRow("Микроорганизм", self.micro_combo)
        micro_form.addRow("Микроорганизм (свободно)", self.micro_free)
        content_layout.addWidget(micro_box)

        # Панели
        self.susc_table = self._make_table(["Антибиотик", "RIS", "MIC", "Метод"], 1)
        self._increase_table_height(self.susc_table)
        self.phage_table = self._make_table(["Фаг", "Свободное имя", "Диаметр"], 1)
        self._increase_table_height(self.phage_table)

        susc_box = QGroupBox("Чувствительность (RIS/MIC)")
        susc_layout = QVBoxLayout(susc_box)
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
        content_layout.addWidget(susc_box)

        phage_box = QGroupBox("Панель фагов")
        phage_layout = QVBoxLayout(phage_box)
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
        content_layout.addWidget(phage_box)

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

        self._load_microbes()
        self._setup_abx_rows()
        self._setup_phage_rows()
        if self.sample_id:
            self._load_existing()

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

    def _increase_table_height(self, table: QTableWidget, multiplier: float = 1.0) -> None:
        base = max(table.sizeHint().height(), 220)
        table.setMinimumHeight(int(base * multiplier))

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
            if bool(self._micro_search_updating):  # type: ignore[has-type]
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

    def _load_existing(self) -> None:
        try:
            if self.sample_id is None:
                return
            sample_id = cast(int, self.sample_id)
            detail = self.sanitary_service.get_detail(sample_id)
            sample = detail["sample"]
            self.sampling_point.setText(sample.sampling_point or "")
            self.room.setText(sample.room or "")
            self.medium.setText(sample.medium or "")
            if sample.taken_at:
                self.taken_at.setDateTime(sample.taken_at)
            if getattr(sample, "delivered_at", None):
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
            iso = detail["isolation"]
            if iso:
                idx = self.micro_combo.findData(iso[0].microorganism_id)
                if idx >= 0:
                    self.micro_combo.setCurrentIndex(idx)
                self.micro_free.setText(iso[0].microorganism_free or "")
            self._fill_susceptibility(detail["susceptibility"])
            self._fill_phages(detail["phages"])

            # Keep editable when editing existing sample.
        except Exception as exc:  # noqa: BLE001
            set_status(self.error_label, str(exc), "error")

    def _collect_susceptibility(self) -> list[dict]:
        items = []
        for row in range(self.susc_table.rowCount()):
            abx_widget = self.susc_table.cellWidget(row, 0)
            abx_combo = cast(QComboBox, abx_widget) if isinstance(abx_widget, QComboBox) else None
            ris_item = self.susc_table.item(row, 1)
            mic_item = self.susc_table.item(row, 2)
            method_item = self.susc_table.item(row, 3)
            abx_id = abx_combo.currentData() if abx_combo else None
            has_any = any(
                [
                    (ris_item and ris_item.text().strip()),
                    (mic_item and mic_item.text().strip()),
                    (method_item and method_item.text().strip()),
                ]
            )
            if has_any and not abx_id:
                raise ValueError(f"Выберите антибиотик в строке {row + 1}")
            if abx_id:
                ris_val = ris_item.text().strip().upper() if ris_item and ris_item.text() else None
                if ris_val and ris_val not in ("R", "I", "S"):
                    raise ValueError("RIS должен быть R/I/S")
                items.append(
                    {
                        "antibiotic_id": abx_id,
                        "ris": ris_val,
                        "mic_mg_l": float(mic_item.text()) if mic_item and mic_item.text() else None,
                        "method": method_item.text() if method_item else None,
                    }
                )
        return items

    def _collect_phages(self) -> list[dict]:
        items = []
        for row in range(self.phage_table.rowCount()):
            ph_widget = self.phage_table.cellWidget(row, 0)
            ph_combo = cast(QComboBox, ph_widget) if isinstance(ph_widget, QComboBox) else None
            free_item = self.phage_table.item(row, 1)
            dia_item = self.phage_table.item(row, 2)
            ph_id = ph_combo.currentData() if ph_combo else None
            free_text = free_item.text().strip() if free_item and free_item.text() else ""
            has_any = bool(free_text) or (dia_item and dia_item.text().strip())
            if has_any and not ph_id and not free_text:
                raise ValueError(f"Укажите фаг или свободное имя в строке {row + 1}")
            if ph_id or free_text:
                dia_val = float(dia_item.text()) if dia_item and dia_item.text() else None
                if dia_val is not None and dia_val < 0:
                    raise ValueError("Диаметр должен быть >= 0")
                items.append(
                    {
                        "phage_id": ph_id,
                        "phage_free": free_text or None,
                        "lysis_diameter_mm": dia_val,
                    }
                )
        return items

    def _has_result_data(self) -> bool:
        if self.growth_flag.currentData() is not None:
            return True
        if any(
            [
                self.colony_desc.text().strip(),
                self.microscopy.text().strip(),
                self.cfu.text().strip(),
                self.micro_combo.currentData() is not None,
                self.micro_free.text().strip(),
            ]
        ):
            return True
        for row in range(self.susc_table.rowCount()):
            abx_widget = self.susc_table.cellWidget(row, 0)
            abx_combo = cast(QComboBox, abx_widget) if isinstance(abx_widget, QComboBox) else None
            if abx_combo and abx_combo.currentData() is not None:
                return True
            for col in range(1, 4):
                item = self.susc_table.item(row, col)
                if item and item.text().strip():
                    return True
        for row in range(self.phage_table.rowCount()):
            ph_widget = self.phage_table.cellWidget(row, 0)
            ph_combo = cast(QComboBox, ph_widget) if isinstance(ph_widget, QComboBox) else None
            if ph_combo and ph_combo.currentData() is not None:
                return True
            for col in range(1, 3):
                item = self.phage_table.item(row, col)
                if item and item.text().strip():
                    return True
        return False

    def on_save(self) -> None:
        clear_status(self.error_label)
        if self.sample_id is None:
            try:
                if not self.sampling_point.text().strip():
                    raise ValueError("Укажите точку отбора")
                req = SanitarySampleCreateRequest(
                    department_id=self.department_id,
                    sampling_point=self.sampling_point.text().strip(),
                    room=self.room.text().strip() or None,
                    medium=self.medium.text().strip() or None,
                    taken_at=cast(datetime | None, self.taken_at.dateTime().toPython())
                    if self.taken_at.dateTime().isValid()
                    else None,
                    delivered_at=cast(datetime | None, self.delivered_at.dateTime().toPython())
                    if self.delivered_at.dateTime().isValid()
                    else None,
                    created_by=None,
                )
                resp = self.sanitary_service.create_sample(req)
                self.sample_id = resp.id
                if self._has_result_data():
                    upd = SanitarySampleResultUpdate(
                        growth_flag=self.growth_flag.currentData(),
                        growth_result_at=cast(datetime | None, self.growth_result_at.dateTime().toPython())
                        if self.growth_result_at.dateTime().isValid()
                        else datetime.now(UTC),
                        colony_desc=self.colony_desc.text() or None,
                        microscopy=self.microscopy.text() or None,
                        cfu=self.cfu.text() or None,
                        microorganism_id=self.micro_combo.currentData(),
                        microorganism_free=self.micro_free.text() or None,
                        susceptibility=self._collect_susceptibility(),
                        phages=self._collect_phages(),
                    )
                    self.sanitary_service.update_result(self.sample_id, upd, actor_id=None)
                self.accept()
            except Exception as exc:  # noqa: BLE001
                set_status(self.error_label, str(exc), "error")
        else:
            try:
                if not self.sampling_point.text().strip():
                    raise ValueError("Укажите точку отбора")
                upd_sample = SanitarySampleUpdateRequest(
                    sampling_point=self.sampling_point.text().strip() or None,
                    room=self.room.text().strip() or None,
                    medium=self.medium.text().strip() or None,
                    taken_at=cast(datetime | None, self.taken_at.dateTime().toPython())
                    if self.taken_at.dateTime().isValid()
                    else None,
                    delivered_at=cast(datetime | None, self.delivered_at.dateTime().toPython())
                    if self.delivered_at.dateTime().isValid()
                    else None,
                )
                self.sanitary_service.update_sample(self.sample_id, upd_sample, actor_id=None)
                upd = SanitarySampleResultUpdate(
                    growth_flag=self.growth_flag.currentData(),
                    growth_result_at=cast(datetime | None, self.growth_result_at.dateTime().toPython())
                    if self.growth_result_at.dateTime().isValid()
                    else datetime.now(UTC),
                    colony_desc=self.colony_desc.text() or None,
                    microscopy=self.microscopy.text() or None,
                    cfu=self.cfu.text() or None,
                    microorganism_id=self.micro_combo.currentData(),
                    microorganism_free=self.micro_free.text() or None,
                    susceptibility=self._collect_susceptibility(),
                    phages=self._collect_phages(),
                )
                self.sanitary_service.update_result(self.sample_id, upd, actor_id=None)
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
