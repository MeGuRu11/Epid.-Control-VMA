from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast

from PySide6.QtCore import QDate, QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QComboBox,
    QCompleter,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
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

from app.application.dto.sanitary_dto import SanitarySampleResultUpdate
from app.application.exceptions import AppError
from app.application.services.reference_service import ReferenceService
from app.application.services.sanitary_sample_payload_service import (
    PhageInput,
    SusceptibilityInput,
    build_phage_payload,
    build_sanitary_result_update,
    build_sanitary_sample_create_request,
    build_sanitary_sample_update_request,
    build_susceptibility_payload,
    has_sanitary_result_data,
)
from app.application.services.sanitary_service import SanitaryService
from app.ui.sanitary.history_view_helpers import (
    HistorySummary,
    build_sample_context_line,
    build_sample_details_line,
    filter_and_sort_samples,
    paginate_samples,
    resolve_micro_text,
    summarize_history,
)
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.datetime_inputs import create_optional_datetime_edit, optional_datetime_value
from app.ui.widgets.dialog_utils import localize_button_box
from app.ui.widgets.notifications import clear_status, error_text, set_status
from app.ui.widgets.responsive_actions import ResponsiveActionsPanel
from app.ui.widgets.table_utils import (
    connect_combo_autowidth,
    connect_combo_resize_on_content,
    resize_columns_to_content,
)

_HANDLED_SANITARY_ERRORS = (ValueError, RuntimeError, LookupError, TypeError, AppError)


class SanitaryHistoryDialog(QDialog):
    references_updated = Signal()
    _micro_search_updating: bool = False

    def __init__(
        self,
        sanitary_service: SanitaryService,
        reference_service: ReferenceService,
        department_id: int,
        department_name: str,
        actor_id: int | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.sanitary_service = sanitary_service
        self.reference_service = reference_service
        self.department_id = department_id
        self.department_name = department_name
        self.actor_id = actor_id
        self._microbe_map: dict[int, str] = {}
        self._micro_search_updating: bool = False
        self._date_empty = QDate(2000, 1, 1)
        self._last_empty_state: str | None = None
        self.page_index = 1
        self.page_size = 50
        self.setWindowTitle(f"Санитарные пробы - {department_name}")
        parent_signal = getattr(parent, "references_updated", None)
        if parent_signal is not None and hasattr(parent_signal, "connect"):
            parent_signal.connect(self._on_references_updated)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        self.setMinimumSize(560, 620)
        self.resize(1040, 760)

        title = QLabel("История санитарных проб")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.department_label = QLabel(f"Отделение: {self.department_name or self.department_id}")
        self.department_label.setObjectName("homeUserInfo")
        layout.addWidget(self.department_label)

        self.hint_label = QLabel("Двойное нажатие по записи открывает карточку санитарной пробы.")
        self.hint_label.setObjectName("sanitaryHistoryMeta")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        self._summary_card = QWidget()
        self._summary_card.setObjectName("sanitaryHistorySummaryCard")
        summary_layout = QGridLayout(self._summary_card)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        summary_layout.setHorizontalSpacing(18)
        summary_layout.setVerticalSpacing(10)
        self._summary_total_value = self._build_summary_field(summary_layout, 0, 0, "Всего проб")
        self._summary_positive_value = self._build_summary_field(summary_layout, 0, 1, "Положительные")
        self._summary_last_value = self._build_summary_field(summary_layout, 1, 0, "Последняя проба")
        self._summary_shown_value = self._build_summary_field(summary_layout, 1, 1, "Показано на странице")
        layout.addWidget(self._summary_card)

        filter_box = QGroupBox("Фильтры")
        filter_shell = QVBoxLayout(filter_box)
        filter_shell.setContentsMargins(10, 8, 10, 10)
        filter_shell.setSpacing(8)

        self._filter_bar = QWidget()
        self._filter_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._filter_bar)
        self._filter_layout.setContentsMargins(0, 0, 0, 0)
        self._filter_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по номеру пробы")
        self.search_input.textChanged.connect(self._on_filter_changed)
        self._search_group = QWidget()
        search_layout = QVBoxLayout(self._search_group)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)
        search_label = QLabel("Номер пробы")
        search_label.setObjectName("sanitaryHistoryMeta")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)

        self.growth_filter = QComboBox()
        self.growth_filter.addItem("Выбрать", None)
        self.growth_filter.addItem("Положительные", 1)
        self.growth_filter.addItem("Отрицательные", 0)
        connect_combo_autowidth(self.growth_filter)
        self.growth_filter.currentIndexChanged.connect(self._on_filter_changed)
        self._growth_group = QWidget()
        growth_layout = QVBoxLayout(self._growth_group)
        growth_layout.setContentsMargins(0, 0, 0, 0)
        growth_layout.setSpacing(4)
        growth_label = QLabel("Рост")
        growth_label.setObjectName("sanitaryHistoryMeta")
        growth_layout.addWidget(growth_label)
        growth_layout.addWidget(self.growth_filter)

        self.date_from = QDateTimeEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setMinimumDate(self._date_empty)
        self.date_from.setSpecialValueText("")
        self.date_from.setDate(self._date_empty)
        self.date_from.dateChanged.connect(self._on_filter_changed)

        self.date_to = QDateTimeEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setMinimumDate(self._date_empty)
        self.date_to.setSpecialValueText("")
        self.date_to.setDate(self._date_empty)
        self.date_to.dateChanged.connect(self._on_filter_changed)

        self._date_group = QWidget()
        date_layout = QGridLayout(self._date_group)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setHorizontalSpacing(8)
        date_layout.setVerticalSpacing(4)
        date_from_label = QLabel("Дата от")
        date_from_label.setObjectName("sanitaryHistoryMeta")
        date_to_label = QLabel("Дата до")
        date_to_label.setObjectName("sanitaryHistoryMeta")
        date_layout.addWidget(date_from_label, 0, 0)
        date_layout.addWidget(self.date_from, 0, 1)
        date_layout.addWidget(date_to_label, 1, 0)
        date_layout.addWidget(self.date_to, 1, 1)

        clear_filters_btn = QPushButton("Сбросить")
        compact_button(clear_filters_btn)
        clear_filters_btn.clicked.connect(self._clear_filters)
        self._filter_actions_group = QWidget()
        filter_actions_layout = QVBoxLayout(self._filter_actions_group)
        filter_actions_layout.setContentsMargins(0, 0, 0, 0)
        filter_actions_layout.setSpacing(4)
        actions_label = QLabel("Действия")
        actions_label.setObjectName("sanitaryHistoryMeta")
        filter_actions_layout.addWidget(actions_label)
        filter_actions_layout.addWidget(clear_filters_btn)
        filter_actions_layout.addStretch(1)

        self._filter_layout.addWidget(self._search_group, 2)
        self._filter_layout.addWidget(self._growth_group, 1)
        self._filter_layout.addWidget(self._date_group, 2)
        self._filter_layout.addWidget(self._filter_actions_group)
        filter_shell.addWidget(self._filter_bar)

        self.filter_summary_label = QLabel("Без фильтров")
        self.filter_summary_label.setObjectName("sanitaryHistoryMeta")
        self.filter_summary_label.setWordWrap(True)
        filter_shell.addWidget(self.filter_summary_label)
        layout.addWidget(filter_box)

        list_box = QGroupBox("История проб")
        list_layout = QVBoxLayout(list_box)
        list_layout.setContentsMargins(10, 8, 10, 10)
        list_layout.setSpacing(8)

        self._list_header_bar = QWidget()
        self._list_header_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._list_header_bar)
        self._list_header_layout.setContentsMargins(0, 0, 0, 0)
        self._list_header_layout.setSpacing(10)

        self._list_summary_group = QWidget()
        list_summary_layout = QHBoxLayout(self._list_summary_group)
        list_summary_layout.setContentsMargins(0, 0, 0, 0)
        list_summary_layout.setSpacing(6)
        self.list_summary_label = QLabel("Найдено 0 проб • показано 0")
        self.list_summary_label.setObjectName("sanitaryHistoryMeta")
        self.list_summary_label.setWordWrap(True)
        list_summary_layout.addWidget(self.list_summary_label)

        self._paging_group = QWidget()
        paging_layout = QHBoxLayout(self._paging_group)
        paging_layout.setContentsMargins(0, 0, 0, 0)
        paging_layout.setSpacing(8)
        self.page_label = QLabel("Стр. 1 / 1")
        self.page_label.setObjectName("sanitaryHistoryMeta")
        self.prev_btn = QPushButton("Назад")
        compact_button(self.prev_btn)
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn = QPushButton("Вперёд")
        compact_button(self.next_btn)
        self.next_btn.clicked.connect(self._next_page)
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["20", "50", "100"])
        self.page_size_combo.setCurrentText(str(self.page_size))
        connect_combo_autowidth(self.page_size_combo)
        self.page_size_combo.currentIndexChanged.connect(self._on_page_size_changed)
        paging_layout.addWidget(QLabel("На странице"))
        paging_layout.addWidget(self.page_size_combo)
        paging_layout.addStretch()
        paging_layout.addWidget(self.prev_btn)
        paging_layout.addWidget(self.next_btn)
        paging_layout.addWidget(self.page_label)

        self._list_header_layout.addWidget(self._list_summary_group, 1)
        self._list_header_layout.addWidget(self._paging_group)
        list_layout.addWidget(self._list_header_bar)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(8)
        self.list_widget.setMinimumHeight(260)
        self.list_widget.itemDoubleClicked.connect(self._handle_item_double_clicked)
        list_layout.addWidget(self.list_widget, 1)
        layout.addWidget(list_box, 1)

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
        actions_layout.addWidget(self._actions_panel)
        layout.addWidget(actions_box)

        self._update_filter_layout()
        self._update_list_header_layout()
        self.refresh()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_filter_layout()
        self._update_list_header_layout()

    def _build_summary_field(self, layout: QGridLayout, row: int, column: int, title: str) -> QLabel:
        field = QWidget()
        field.setObjectName("sanitaryHistorySummaryField")
        field_layout = QVBoxLayout(field)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("patientFieldTitle")
        value_label = QLabel("-")
        value_label.setObjectName("patientFieldValue")
        value_label.setWordWrap(True)
        field_layout.addWidget(title_label)
        field_layout.addWidget(value_label)
        layout.addWidget(field, row, column)
        return value_label

    def _update_filter_layout(self) -> None:
        spacing = max(0, self._filter_layout.spacing())
        margins = self._filter_layout.contentsMargins()
        required_width = (
            self._search_group.minimumSizeHint().width()
            + self._growth_group.minimumSizeHint().width()
            + self._date_group.minimumSizeHint().width()
            + self._filter_actions_group.minimumSizeHint().width()
            + spacing * 3
            + margins.left()
            + margins.right()
        )
        direction = (
            QBoxLayout.Direction.LeftToRight
            if self.width() >= max(required_width + 80, 760)
            else QBoxLayout.Direction.TopToBottom
        )
        self._filter_layout.setDirection(direction)

    def _update_list_header_layout(self) -> None:
        spacing = max(0, self._list_header_layout.spacing())
        margins = self._list_header_layout.contentsMargins()
        required_width = (
            self._list_summary_group.minimumSizeHint().width()
            + self._paging_group.minimumSizeHint().width()
            + spacing
            + margins.left()
            + margins.right()
        )
        direction = (
            QBoxLayout.Direction.LeftToRight
            if self.width() >= required_width + 48
            else QBoxLayout.Direction.TopToBottom
        )
        self._list_header_layout.setDirection(direction)

    def refresh(self) -> None:
        self.list_widget.clear()
        self._load_microbe_map()
        samples = list(self.sanitary_service.list_samples_by_department(self.department_id))
        search = self.search_input.text().strip().lower()
        growth = self.growth_filter.currentData()
        date_from = self._date_value(self.date_from)
        date_to = self._date_value(self.date_to)
        filtered = filter_and_sort_samples(
            samples,
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
        shown = len(page_state.page_items)
        self._update_summary(summary, shown)
        self._update_filter_summary(
            search=search,
            growth=growth,
            date_from=date_from,
            date_to=date_to,
        )
        self.list_summary_label.setText(f"Найдено {summary.total} проб • показано {shown}")

        if not page_state.page_items:
            if not samples:
                self._add_empty_item(
                    "no_data",
                    "Проб пока нет",
                    "Для этого отделения санитарные пробы ещё не зарегистрированы.",
                )
            else:
                self._add_empty_item(
                    "filtered_out",
                    "По фильтрам ничего не найдено",
                    "Попробуйте ослабить условия отбора или нажать «Сбросить».",
                )
            self._update_paging(summary.total)
            return

        self._last_empty_state = None
        for sample in page_state.page_items:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, sample.id)
            card = self._build_sample_item(sample)
            item.setSizeHint(card.sizeHint().expandedTo(card.minimumSizeHint()))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, card)
        self._update_paging(summary.total)

    def _build_sample_item(self, sample: Any) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("sanitaryHistoryListCard")
        wrapper.setMinimumHeight(86)

        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title_group = QWidget()
        title_group_layout = QHBoxLayout(title_group)
        title_group_layout.setContentsMargins(0, 0, 0, 0)
        title_group_layout.setSpacing(6)

        title = QLabel(sample.lab_no or f"Проба #{sample.id}")
        title.setObjectName("cardTitle")
        sample_id = QLabel(f"id {sample.id}")
        sample_id.setObjectName("sanitaryHistoryMeta")
        title_group_layout.addWidget(title)
        title_group_layout.addWidget(sample_id)
        title_group_layout.addStretch()

        if sample.growth_flag == 1:
            badge_text = "Положительная"
            badge_tone = "positive"
        elif sample.growth_flag == 0:
            badge_text = "Отрицательная"
            badge_tone = "success"
        else:
            badge_text = "Без результата"
            badge_tone = "warning"

        badge = QLabel(badge_text)
        badge.setObjectName("sanitaryHistoryBadge")
        badge.setProperty("tone", badge_tone)

        header.addWidget(title_group, 1)
        header.addStretch()
        header.addWidget(badge)
        layout.addLayout(header)

        micro_text = resolve_micro_text(sample, microbe_map=self._microbe_map)
        details_line = QLabel(build_sample_details_line(sample, micro_text=micro_text))
        details_line.setObjectName("sanitaryHistoryMeta")
        details_line.setWordWrap(True)
        layout.addWidget(details_line)

        context_line = QLabel(build_sample_context_line(sample))
        context_line.setObjectName("sanitaryHistoryMeta")
        context_line.setWordWrap(True)
        layout.addWidget(context_line)
        return wrapper

    def _build_empty_card(self, title: str, detail: str) -> QWidget:
        card = QWidget()
        card.setObjectName("sanitaryHistoryEmptyCard")
        card.setMinimumHeight(112)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        detail_label = QLabel(detail)
        detail_label.setObjectName("sanitaryHistoryMeta")
        detail_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(detail_label)
        layout.addStretch(1)
        return card

    def _add_empty_item(self, state: str, title: str, detail: str) -> None:
        self._last_empty_state = state
        item = QListWidgetItem()
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        card = self._build_empty_card(title, detail)
        item.setSizeHint(card.sizeHint().expandedTo(card.minimumSizeHint()))
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, card)

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

    def _update_summary(self, summary: HistorySummary, shown: int) -> None:
        self._summary_total_value.setText(str(summary.total))
        self._summary_positive_value.setText(str(summary.positives))
        self._summary_last_value.setText(summary.last_taken_text)
        self._summary_shown_value.setText(str(shown))

    def _update_filter_summary(
        self,
        *,
        search: str,
        growth: int | None,
        date_from: date | None,
        date_to: date | None,
    ) -> None:
        parts: list[str] = []
        if search:
            parts.append(f"Номер: {search}")
        if growth is not None:
            parts.append(f"Рост: {self.growth_filter.currentText()}")
        if date_from is not None and date_to is not None:
            parts.append(f"Даты: {date_from.strftime('%d.%m.%Y')} — {date_to.strftime('%d.%m.%Y')}")
        elif date_from is not None:
            parts.append(f"Дата с: {date_from.strftime('%d.%m.%Y')}")
        elif date_to is not None:
            parts.append(f"Дата до: {date_to.strftime('%d.%m.%Y')}")
        self.filter_summary_label.setText(" • ".join(parts) if parts else "Без фильтров")

    def _update_paging(self, total: int) -> None:
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

    def _handle_item_double_clicked(self, item: QListWidgetItem) -> None:
        self.list_widget.setCurrentItem(item)
        self._edit_selected()

    def _open_new_dialog(self) -> None:
        dlg = SanitarySampleDetailDialog(
            self.sanitary_service,
            self.reference_service,
            department_id=self.department_id,
            actor_id=self.actor_id,
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
            actor_id=self.actor_id,
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
    _micro_search_updating: bool = False

    def __init__(
        self,
        sanitary_service: SanitaryService,
        reference_service: ReferenceService,
        department_id: int,
        actor_id: int | None,
        sample_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.sanitary_service = sanitary_service
        self.reference_service = reference_service
        self.department_id = department_id
        self.actor_id = actor_id
        self.sample_id = sample_id
        self._abx_list: list[Any] = []
        self._phage_list: list[Any] = []
        self._micro_search_updating = False
        self.setWindowTitle("Санитарная проба")
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setSizeGripEnabled(True)
        self._build_ui()
        self._apply_initial_size()

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

        self.sampling_point = QLineEdit()
        self.room = QLineEdit()
        self.medium = QLineEdit()
        self.taken_at = create_optional_datetime_edit()
        self.delivered_at = create_optional_datetime_edit()

        main_box = QGroupBox("Основные данные")
        main_form = QFormLayout(main_box)
        main_form.addRow("Точка отбора", self.sampling_point)
        main_form.addRow("Помещение", self.room)
        main_form.addRow("Среда", self.medium)
        main_form.addRow("Время взятия", self.taken_at)
        main_form.addRow("Дата доставки", self.delivered_at)
        content_layout.addWidget(main_box)

        self.growth_flag = QComboBox()
        self.growth_flag.addItem("Выбрать", None)
        self.growth_flag.addItem("Нет", 0)
        self.growth_flag.addItem("Да", 1)
        self.growth_result_at = create_optional_datetime_edit()
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
        localize_button_box(buttons)
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

    def _apply_initial_size(self) -> None:
        app = QApplication.instance()
        if app is None:
            self.resize(1100, 900)
            self.setMinimumSize(800, 620)
            return
        assert isinstance(app, QApplication)
        screen = self.screen() or app.primaryScreen()
        if screen is None:
            self.resize(1100, 900)
            self.setMinimumSize(800, 620)
            return

        geometry = screen.availableGeometry()
        min_width = min(900, max(760, geometry.width() - 80))
        min_height = min(700, max(580, geometry.height() - 80))
        max_width = max(min_width, geometry.width() - 24)
        max_height = max(min_height, geometry.height() - 24)
        target_width = max(min_width, min(1280, int(geometry.width() * 0.86), max_width))
        target_height = max(min_height, min(980, int(geometry.height() * 0.9), max_height))

        self.setMinimumSize(min_width, min_height)
        self.resize(target_width, target_height)

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
        except _HANDLED_SANITARY_ERRORS as exc:
            set_status(self.error_label, error_text(exc, "Не удалось загрузить справочник микроорганизмов"), "error")

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
            connect_combo_resize_on_content(self.susc_table, combo, row)
        resize_columns_to_content(self.susc_table)

    def _setup_phage_rows(self) -> None:
        self._phage_list = self.reference_service.list_phages()
        for row in range(self.phage_table.rowCount()):
            combo = self._create_phage_combo()
            self.phage_table.setCellWidget(row, 0, combo)
            connect_combo_resize_on_content(self.phage_table, combo, row)
        resize_columns_to_content(self.phage_table)

    def _refresh_abx_combos(self, selected_ids: list[int | None]) -> None:
        self._abx_list = self.reference_service.list_antibiotics()
        for row in range(self.susc_table.rowCount()):
            combo = self._create_abx_combo()
            if row < len(selected_ids) and selected_ids[row] is not None:
                idx = combo.findData(selected_ids[row])
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            self.susc_table.setCellWidget(row, 0, combo)
            connect_combo_resize_on_content(self.susc_table, combo, row)
        resize_columns_to_content(self.susc_table)

    def _refresh_phage_combos(self, selected_ids: list[int | None]) -> None:
        self._phage_list = self.reference_service.list_phages()
        for row in range(self.phage_table.rowCount()):
            combo = self._create_phage_combo()
            if row < len(selected_ids) and selected_ids[row] is not None:
                idx = combo.findData(selected_ids[row])
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            self.phage_table.setCellWidget(row, 0, combo)
            connect_combo_resize_on_content(self.phage_table, combo, row)
        resize_columns_to_content(self.phage_table)

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
        connect_combo_resize_on_content(self.susc_table, combo, row)

    def _add_phage_row(self) -> None:
        row = self.phage_table.rowCount()
        self.phage_table.insertRow(row)
        combo = self._create_phage_combo()
        self.phage_table.setCellWidget(row, 0, combo)
        connect_combo_resize_on_content(self.phage_table, combo, row)

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
        except _HANDLED_SANITARY_ERRORS as exc:
            set_status(self.error_label, error_text(exc, "Не удалось загрузить пробу"), "error")

    def _collect_susceptibility_inputs(self) -> list[SusceptibilityInput]:
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
        return rows

    def _collect_phage_inputs(self) -> list[PhageInput]:
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
        return rows

    def _collect_susceptibility(self) -> list[dict]:
        return build_susceptibility_payload(self._collect_susceptibility_inputs())

    def _collect_phages(self) -> list[dict]:
        return build_phage_payload(self._collect_phage_inputs())

    def _has_result_data(self) -> bool:
        return has_sanitary_result_data(
            growth_flag=self.growth_flag.currentData(),
            colony_desc=self.colony_desc.text(),
            microscopy=self.microscopy.text(),
            cfu=self.cfu.text(),
            microorganism_id=self.micro_combo.currentData(),
            microorganism_free=self.micro_free.text(),
            susceptibility_rows=self._collect_susceptibility_inputs(),
            phage_rows=self._collect_phage_inputs(),
        )

    def _build_result_update(self) -> tuple[bool, SanitarySampleResultUpdate]:
        has_results = self._has_result_data()
        susceptibility = self._collect_susceptibility() if has_results else []
        phages = self._collect_phages() if has_results else []
        update = build_sanitary_result_update(
            has_results=has_results,
            growth_flag=self.growth_flag.currentData(),
            growth_result_at=self._to_python_datetime(self.growth_result_at),
            colony_desc=self.colony_desc.text(),
            microscopy=self.microscopy.text(),
            cfu=self.cfu.text(),
            microorganism_id=self.micro_combo.currentData(),
            microorganism_free=self.micro_free.text(),
            susceptibility=susceptibility,
            phages=phages,
        )
        return has_results, update

    @staticmethod
    def _to_python_datetime(widget: QDateTimeEdit) -> datetime | None:
        return optional_datetime_value(widget)

    def on_save(self) -> None:
        clear_status(self.error_label)
        if self.actor_id is None:
            set_status(self.error_label, "Не удалось определить пользователя сессии", "error")
            return
        if self.sample_id is None:
            try:
                req = build_sanitary_sample_create_request(
                    department_id=self.department_id,
                    sampling_point=self.sampling_point.text(),
                    room=self.room.text(),
                    medium=self.medium.text(),
                    taken_at=self._to_python_datetime(self.taken_at),
                    delivered_at=self._to_python_datetime(self.delivered_at),
                    created_by=None,
                )
                resp = self.sanitary_service.create_sample(req, actor_id=self.actor_id)
                self.sample_id = resp.id
                has_results, result_update = self._build_result_update()
                if has_results:
                    self.sanitary_service.update_result(self.sample_id, result_update, actor_id=self.actor_id)
                self.accept()
            except _HANDLED_SANITARY_ERRORS as exc:
                set_status(self.error_label, error_text(exc, "Не удалось сохранить пробу"), "error")
        else:
            try:
                upd_sample = build_sanitary_sample_update_request(
                    sampling_point=self.sampling_point.text(),
                    room=self.room.text(),
                    medium=self.medium.text(),
                    taken_at=self._to_python_datetime(self.taken_at),
                    delivered_at=self._to_python_datetime(self.delivered_at),
                )
                self.sanitary_service.update_sample(self.sample_id, upd_sample, actor_id=self.actor_id)
                _, result_update = self._build_result_update()
                self.sanitary_service.update_result(self.sample_id, result_update, actor_id=self.actor_id)
                self.accept()
            except _HANDLED_SANITARY_ERRORS as exc:
                set_status(self.error_label, error_text(exc, "Не удалось обновить пробу"), "error")

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
        resize_columns_to_content(self.susc_table)

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
            self.phage_table.setItem(
                idx,
                2,
                QTableWidgetItem(str(r.lysis_diameter_mm) if r.lysis_diameter_mm is not None else ""),
            )
        resize_columns_to_content(self.phage_table)
