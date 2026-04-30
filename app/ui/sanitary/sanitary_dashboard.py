from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import cast

from PySide6.QtCore import QDate, QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.auth_dto import SessionContext
from app.application.dto.sanitary_dto import SanitarySampleResponse
from app.application.services.reference_service import ReferenceService
from app.application.services.sanitary_service import SanitaryService
from app.ui.sanitary.sanitary_history import SanitaryHistoryDialog
from app.ui.widgets.action_bar_layout import update_action_bar_direction
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.table_utils import connect_combo_autowidth


@dataclass(frozen=True, slots=True)
class SanitaryKpiSpec:
    key: str
    title: str
    badge: str
    detail: str
    tone: str


@dataclass(slots=True)
class SanitaryKpiWidgets:
    value_label: QLabel
    detail_label: QLabel


@dataclass(slots=True)
class SanitaryDepartmentEntry:
    dep_id: int
    name: str
    filtered_samples: list[SanitarySampleResponse]
    total_count: int
    positive_count: int
    pending_count: int
    last_sample: SanitarySampleResponse | None


SANITARY_KPI_SPECS = (
    SanitaryKpiSpec("departments", "Отделений в выборке", "DEP", "по активным фильтрам", "context"),
    SanitaryKpiSpec("samples", "Всего проб", "SAN", "по активным фильтрам", "pending"),
    SanitaryKpiSpec("positive", "Положительные", "POS", "с положительным ростом", "positive"),
    SanitaryKpiSpec("pending", "Без результата", "NR", "ожидают результата", "warning"),
)


class SanitaryDashboard(QWidget):
    references_updated = Signal()

    def __init__(
        self,
        sanitary_service: SanitaryService,
        reference_service: ReferenceService,
        session: SessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.sanitary_service = sanitary_service
        self.reference_service = reference_service
        self._session = session
        self._date_empty = QDate(2000, 1, 1)
        self._microbe_map: dict[int, str] = {}
        self._kpi_widgets: dict[str, SanitaryKpiWidgets] = {}
        self._kpi_cards: list[QWidget] = []
        self._entries: list[SanitaryDepartmentEntry] = []
        self._list_item_widgets: list[QWidget] = []
        self._initial_refresh_pending = False
        self._selected_department_id: int | None = None
        self._selected_department_name = ""
        self._last_empty_state: str | None = None
        self._build_ui()

    def set_session(self, session: SessionContext) -> None:
        self._session = session

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setObjectName("sanitaryPageScrollArea")
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        root_layout.addWidget(self._scroll_area)

        self._scroll_content = QWidget()
        self._scroll_area.setWidget(self._scroll_content)

        layout = QVBoxLayout(self._scroll_content)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        self._hero_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._hero_layout.setContentsMargins(0, 0, 0, 0)
        self._hero_layout.setSpacing(16)

        self._hero_card = self._build_hero_card()
        self._utility_card = self._build_utility_card()
        self._hero_layout.addWidget(self._hero_card, 1)
        self._hero_layout.addWidget(self._utility_card, 0)
        self._hero_layout.setStretch(0, 2)
        self._hero_layout.setStretch(1, 1)
        layout.addLayout(self._hero_layout)

        self._filter_card = self._build_filter_card()
        layout.addWidget(self._filter_card)

        self._list_card = self._build_list_card()
        layout.addWidget(self._list_card, 1)

        self._apply_hero_layout()
        self._update_filter_layout()
        self._reflow_utility_kpis()
        self._update_filter_summary()
        self._update_selection_context()
        self._sync_action_state()
        self._initial_refresh_pending = True
        QTimer.singleShot(0, self._run_initial_refresh)

    def _run_initial_refresh(self) -> None:
        if not self._initial_refresh_pending:
            return
        self.refresh()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_quick_actions_layout()
        self._apply_hero_layout()
        self._update_filter_layout()
        self._reflow_utility_kpis()

    def _build_hero_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("sanitaryHeroCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("Санитария")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel("Рабочая лента санитарных проб по отделениям с быстрым переходом к детальной истории.")
        subtitle.setObjectName("sanitaryListMeta")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        context_grid = QGridLayout()
        context_grid.setContentsMargins(0, 0, 0, 0)
        context_grid.setHorizontalSpacing(12)
        context_grid.setVerticalSpacing(12)
        department_card, self._department_context_value = self._build_context_card("Выбранное отделение")
        period_card, self._period_context_value = self._build_context_card("Период")
        context_grid.addWidget(department_card, 0, 0)
        context_grid.addWidget(period_card, 0, 1)
        context_grid.setColumnStretch(0, 1)
        context_grid.setColumnStretch(1, 1)
        layout.addLayout(context_grid)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(10)
        status_title = QLabel("Статус выбора")
        status_title.setObjectName("sanitaryContextTitle")
        self._context_badge = self._build_state_badge("", "warning")
        status_row.addWidget(status_title)
        status_row.addWidget(self._context_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        status_row.addStretch()
        layout.addLayout(status_row)

        self._quick_refresh_button = QPushButton("Обновить")
        self._quick_refresh_button.setObjectName("secondaryButton")
        compact_button(self._quick_refresh_button)
        self._quick_refresh_button.clicked.connect(self.refresh)

        self._quick_open_button = QPushButton("Открыть историю отделения")
        self._quick_open_button.setObjectName("primaryButton")
        compact_button(self._quick_open_button)
        self._quick_open_button.clicked.connect(self._open_selected)

        self._quick_actions_bar = QWidget()
        self._quick_actions_bar.setObjectName("sectionActionBar")
        self._quick_actions_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._quick_actions_bar)
        self._quick_actions_layout.setContentsMargins(12, 8, 12, 8)
        self._quick_actions_layout.setSpacing(10)

        self._quick_ops_group = QWidget()
        self._quick_ops_group.setObjectName("sectionActionGroup")
        ops_layout = QHBoxLayout(self._quick_ops_group)
        ops_layout.setContentsMargins(0, 0, 0, 0)
        ops_layout.addWidget(self._quick_refresh_button)

        self._quick_open_group = QWidget()
        self._quick_open_group.setObjectName("sectionActionGroup")
        open_layout = QHBoxLayout(self._quick_open_group)
        open_layout.setContentsMargins(0, 0, 0, 0)
        open_layout.addWidget(self._quick_open_button)

        self._quick_actions_layout.addWidget(self._quick_ops_group)
        self._quick_actions_layout.addStretch()
        self._quick_actions_layout.addWidget(self._quick_open_group)
        layout.addWidget(self._quick_actions_bar)

        self._update_quick_actions_layout()
        return card

    def _build_utility_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("sanitaryUtilityCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Сводка по отделениям")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self._utility_context_label = QLabel("Выборка по всем отделениям.")
        self._utility_context_label.setObjectName("sanitaryListMeta")
        self._utility_context_label.setWordWrap(True)
        layout.addWidget(self._utility_context_label)

        self._utility_grid = QGridLayout()
        self._utility_grid.setContentsMargins(0, 0, 0, 0)
        self._utility_grid.setHorizontalSpacing(12)
        self._utility_grid.setVerticalSpacing(12)
        for spec in SANITARY_KPI_SPECS:
            self._add_kpi_card(spec)
        layout.addLayout(self._utility_grid)
        layout.addStretch()
        return card

    def _build_filter_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("sanitaryFilterCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)
        title = QLabel("Фильтры")
        title.setObjectName("sectionTitle")
        self._filter_summary_label = QLabel("Без фильтров")
        self._filter_summary_label.setObjectName("sanitaryListMeta")
        self.filters_toggle = QPushButton("Показать фильтры")
        self.filters_toggle.setObjectName("secondaryButton")
        compact_button(self.filters_toggle)
        self.filters_toggle.setCheckable(True)
        self.filters_toggle.toggled.connect(self._toggle_filters)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self._filter_summary_label)
        header.addWidget(self.filters_toggle)
        layout.addLayout(header)

        self.filter_box = QWidget()
        self.filter_box.setVisible(False)
        filter_wrapper = QVBoxLayout(self.filter_box)
        filter_wrapper.setContentsMargins(0, 0, 0, 0)
        filter_wrapper.setSpacing(0)

        self._filter_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._filter_layout.setContentsMargins(0, 0, 0, 0)
        self._filter_layout.setSpacing(12)

        self._filter_date_group = QWidget()
        date_layout = QGridLayout(self._filter_date_group)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setHorizontalSpacing(10)
        date_layout.setVerticalSpacing(8)

        self.filter_enabled = QCheckBox("Фильтр по дате")
        self.filter_enabled.setChecked(False)
        self.filter_enabled.stateChanged.connect(self._on_filter_changed)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setMinimumDate(self._date_empty)
        self.date_from.setSpecialValueText("")
        self.date_from.setDate(self._date_empty)
        self.date_from.dateChanged.connect(self._on_filter_changed)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setMinimumDate(self._date_empty)
        self.date_to.setSpecialValueText("")
        self.date_to.setDate(self._date_empty)
        self.date_to.dateChanged.connect(self._on_filter_changed)

        date_layout.addWidget(self.filter_enabled, 0, 0, 1, 2)
        date_layout.addWidget(QLabel("Дата от"), 1, 0)
        date_layout.addWidget(self.date_from, 1, 1)
        date_layout.addWidget(QLabel("Дата до"), 2, 0)
        date_layout.addWidget(self.date_to, 2, 1)
        date_layout.setColumnStretch(1, 1)

        self._filter_query_group = QWidget()
        query_layout = QGridLayout(self._filter_query_group)
        query_layout.setContentsMargins(0, 0, 0, 0)
        query_layout.setHorizontalSpacing(10)
        query_layout.setVerticalSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по отделению")
        self.search_input.textChanged.connect(self._on_filter_changed)

        self.growth_filter = QComboBox()
        self.growth_filter.addItem("Рост: все", None)
        self.growth_filter.addItem("Рост: положительные", 1)
        self.growth_filter.addItem("Рост: отрицательные", 0)
        self.growth_filter.addItem("Рост: не указан", -1)
        connect_combo_autowidth(self.growth_filter)
        self.growth_filter.currentIndexChanged.connect(self._on_filter_changed)

        clear_filters_btn = QPushButton("Сбросить")
        clear_filters_btn.setObjectName("secondaryButton")
        compact_button(clear_filters_btn)
        clear_filters_btn.clicked.connect(self._clear_filters)

        query_layout.addWidget(QLabel("Отделение"), 0, 0)
        query_layout.addWidget(self.search_input, 0, 1)
        query_layout.addWidget(QLabel("Рост"), 1, 0)
        query_layout.addWidget(self.growth_filter, 1, 1)
        query_layout.addWidget(clear_filters_btn, 2, 1, 1, 1, Qt.AlignmentFlag.AlignRight)
        query_layout.setColumnStretch(1, 1)

        self._filter_layout.addWidget(self._filter_date_group, 1)
        self._filter_layout.addWidget(self._filter_query_group, 1)
        filter_wrapper.addLayout(self._filter_layout)
        layout.addWidget(self.filter_box)
        return card

    def _build_list_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("sanitaryListCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        card.setMinimumHeight(380)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Отделения в выборке")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        self.summary_label = QLabel("Найдено 0 отделений • проб 0 • положительных 0")
        self.summary_label.setObjectName("sanitaryListMeta")
        toolbar.addWidget(self.summary_label)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(8)
        self.list_widget.setMinimumHeight(240)
        self.list_widget.itemDoubleClicked.connect(self._handle_item_double_clicked)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget, 1)
        return card

    def _build_context_card(self, title: str) -> tuple[QWidget, QLabel]:
        card = QWidget()
        card.setObjectName("sanitaryContextCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("sanitaryContextTitle")
        value_label = QLabel("-")
        value_label.setObjectName("sanitaryContextValue")
        value_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card, value_label

    def _add_kpi_card(self, spec: SanitaryKpiSpec) -> None:
        card = QWidget()
        card.setObjectName("sanitaryKpiCard")
        card.setProperty("toneKey", spec.key)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        card.setMinimumWidth(180)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        badge = self._build_state_badge(spec.badge, spec.tone)
        title_label = QLabel(spec.title)
        title_label.setObjectName("sanitaryKpiTitle")
        title_label.setWordWrap(True)
        top_row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        top_row.addWidget(title_label, 1)
        layout.addLayout(top_row)

        value_label = QLabel("0")
        value_label.setObjectName("sanitaryKpiValue")
        layout.addWidget(value_label)

        detail_label = QLabel(spec.detail)
        detail_label.setObjectName("sanitaryListMeta")
        detail_label.setWordWrap(True)
        layout.addWidget(detail_label)

        self._kpi_cards.append(card)
        self._kpi_widgets[spec.key] = SanitaryKpiWidgets(value_label=value_label, detail_label=detail_label)

    def _build_state_badge(self, text: str, tone: str) -> QLabel:
        badge = QLabel(text)
        badge.setObjectName("sanitaryStateBadge")
        badge.setProperty("tone", tone)
        return badge

    def _build_department_item(self, entry: SanitaryDepartmentEntry) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("listCard")

        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QLabel(entry.name)
        title.setObjectName("cardTitle")
        state_text = "Есть положительные" if entry.positive_count > 0 else "Без положительных"
        state_tone = "positive" if entry.positive_count > 0 else "success"
        state_badge = self._build_state_badge(state_text, state_tone)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(state_badge)
        layout.addLayout(header)

        middle = QLabel(
            f"Проб: {entry.total_count} • Положительные: {entry.positive_count} • Без результата: {entry.pending_count}"
        )
        middle.setObjectName("sanitaryListMeta")
        middle.setWordWrap(True)
        layout.addWidget(middle)

        bottom_parts = [f"Последняя проба: {self._sample_taken_text(entry.last_sample)}"]
        if entry.last_sample is not None:
            if entry.last_sample.sampling_point:
                bottom_parts.append(f"Точка: {entry.last_sample.sampling_point}")
            if entry.last_sample.room:
                bottom_parts.append(f"Помещение: {entry.last_sample.room}")
            micro_text = self._microbe_label(entry.last_sample)
            if micro_text:
                bottom_parts.append(f"Микроорганизм: {micro_text}")
            elif entry.last_sample.medium:
                bottom_parts.append(f"Среда: {entry.last_sample.medium}")
        bottom = QLabel(" • ".join(bottom_parts))
        bottom.setObjectName("sanitaryListMeta")
        bottom.setWordWrap(True)
        layout.addWidget(bottom)
        return wrapper

    def _build_empty_card(self, title: str, detail: str) -> QWidget:
        card = QWidget()
        card.setObjectName("sanitaryEmptyCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        card.setMinimumHeight(112)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("sanitaryContextValue")
        detail_label = QLabel(detail)
        detail_label.setObjectName("sanitaryListMeta")
        detail_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(detail_label)
        layout.addStretch(1)
        return card

    def _update_quick_actions_layout(self) -> None:
        available_width = max(0, self._scroll_area.viewport().width() - 48)
        if self._quick_actions_bar.width() > 0:
            available_width = min(available_width, self._quick_actions_bar.width())
        update_action_bar_direction(
            self._quick_actions_layout,
            self._quick_actions_bar,
            [self._quick_ops_group, self._quick_open_group],
            extra_width=220,
            available_width=available_width,
        )

    def _apply_hero_layout(self) -> None:
        spacing = max(0, self._hero_layout.spacing())
        margins = self._hero_layout.contentsMargins()
        required_width = (
            self._hero_card.minimumSizeHint().width()
            + self._utility_card.minimumSizeHint().width()
            + spacing
            + margins.left()
            + margins.right()
        )
        direction = (
            QBoxLayout.Direction.LeftToRight
            if self.width() >= required_width
            else QBoxLayout.Direction.TopToBottom
        )
        self._hero_layout.setDirection(direction)
        if direction == QBoxLayout.Direction.LeftToRight:
            self._hero_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._utility_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        else:
            self._hero_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self._utility_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._hero_card.updateGeometry()
        self._utility_card.updateGeometry()

    def _update_filter_layout(self) -> None:
        spacing = max(0, self._filter_layout.spacing())
        margins = self._filter_layout.contentsMargins()
        required_width = (
            self._filter_date_group.minimumSizeHint().width()
            + self._filter_query_group.minimumSizeHint().width()
            + spacing
            + margins.left()
            + margins.right()
            + 80
        )
        available_width = max(0, self._scroll_area.viewport().width() - 32)
        direction = (
            QBoxLayout.Direction.LeftToRight
            if available_width >= required_width
            else QBoxLayout.Direction.TopToBottom
        )
        self._filter_layout.setDirection(direction)
        self._filter_date_group.updateGeometry()
        self._filter_query_group.updateGeometry()

    def _reflow_utility_kpis(self) -> None:
        while self._utility_grid.count():
            item = self._utility_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(self._utility_card)

        if not self._kpi_cards:
            return

        card_min_width = max(card.minimumSizeHint().width() for card in self._kpi_cards)
        spacing = max(0, self._utility_grid.horizontalSpacing())
        margins = self._utility_grid.contentsMargins()
        required_width = card_min_width * 2 + spacing + margins.left() + margins.right()
        columns = 2 if self._utility_card.width() >= required_width else 1

        for idx, card in enumerate(self._kpi_cards):
            row = idx // columns
            column = idx % columns
            self._utility_grid.addWidget(card, row, column)
        self._utility_grid.setColumnStretch(0, 1)
        self._utility_grid.setColumnStretch(1, 1 if columns == 2 else 0)

    def _toggle_filters(self, checked: bool) -> None:
        self.filter_box.setVisible(checked)
        self.filters_toggle.setText("Скрыть фильтры" if checked else "Показать фильтры")

    def _on_filter_changed(self) -> None:
        self.refresh()

    def _clear_filters(self) -> None:
        blockers = [
            QSignalBlocker(self.filter_enabled),
            QSignalBlocker(self.date_from),
            QSignalBlocker(self.date_to),
            QSignalBlocker(self.search_input),
            QSignalBlocker(self.growth_filter),
        ]
        self.filter_enabled.setChecked(False)
        self.date_from.setDate(self._date_empty)
        self.date_to.setDate(self._date_empty)
        self.search_input.clear()
        self.growth_filter.setCurrentIndex(0)
        del blockers
        self.refresh()

    def _date_value(self, editor: QDateEdit) -> date | None:
        current = editor.date()
        if current == self._date_empty:
            return None
        return cast(date, current.toPython())

    def _current_period_text(self) -> str:
        if not self.filter_enabled.isChecked():
            return "Весь период"
        from_date = self._date_value(self.date_from)
        to_date = self._date_value(self.date_to)
        if from_date and to_date and from_date > to_date:
            from_date, to_date = to_date, from_date
        if from_date and to_date:
            return f"{from_date.strftime('%d.%m.%Y')} — {to_date.strftime('%d.%m.%Y')}"
        if from_date:
            return f"с {from_date.strftime('%d.%m.%Y')}"
        if to_date:
            return f"до {to_date.strftime('%d.%m.%Y')}"
        return "Весь период"

    def _update_filter_summary(self) -> None:
        parts: list[str] = []
        search = self.search_input.text().strip()
        if search:
            parts.append(f"Отделение: {search}")
        if self.filter_enabled.isChecked():
            period_text = self._current_period_text()
            if period_text != "Весь период":
                parts.append(f"Даты: {period_text}")
        growth_value = self.growth_filter.currentData()
        if growth_value is not None:
            parts.append(self.growth_filter.currentText())
        self._filter_summary_label.setText(" • ".join(parts) if parts else "Без фильтров")

    def _update_selection_context(self) -> None:
        self._period_context_value.setText(self._current_period_text())
        if self._selected_department_id is None:
            self._department_context_value.setText("Не выбрано")
            if self._filter_summary_label.text() == "Без фильтров":
                self._utility_context_label.setText("Выборка по всем отделениям.")
            else:
                self._utility_context_label.setText(f"Текущая выборка: {self._filter_summary_label.text()}.")
            self._set_context_badge("Выберите отделение", "warning")
            return

        self._department_context_value.setText(self._selected_department_name)
        if self._filter_summary_label.text() == "Без фильтров":
            self._utility_context_label.setText(f"Текущая выборка по всем отделениям. Выбрано: {self._selected_department_name}.")
        else:
            self._utility_context_label.setText(
                f"Текущая выборка: {self._filter_summary_label.text()}. Выбрано: {self._selected_department_name}."
            )
        self._set_context_badge("Отделение выбрано", "context")

    def _set_context_badge(self, text: str, tone: str) -> None:
        self._context_badge.setText(text)
        self._context_badge.setProperty("tone", tone)
        style = self._context_badge.style()
        style.unpolish(self._context_badge)
        style.polish(self._context_badge)
        self._context_badge.update()

    def _update_kpis(self, entries: list[SanitaryDepartmentEntry]) -> None:
        values = {
            "departments": len(entries),
            "samples": sum(entry.total_count for entry in entries),
            "positive": sum(entry.positive_count for entry in entries),
            "pending": sum(entry.pending_count for entry in entries),
        }
        for spec in SANITARY_KPI_SPECS:
            widgets = self._kpi_widgets[spec.key]
            widgets.value_label.setText(str(values[spec.key]))
            widgets.detail_label.setText(spec.detail)

    def _load_microbe_map(self) -> None:
        loader = getattr(self.reference_service, "list_microorganisms", None)
        self._microbe_map = {}
        if not callable(loader):
            return
        for item in loader():
            micro_id = getattr(item, "id", None)
            micro_name = getattr(item, "name", None)
            if isinstance(micro_id, int) and isinstance(micro_name, str):
                self._microbe_map[micro_id] = micro_name

    def _collect_entries(self) -> tuple[list[SanitaryDepartmentEntry], str | None]:
        departments = list(self.reference_service.list_departments())
        if not departments:
            return [], "no_data"

        search = self.search_input.text().strip().lower()
        growth_filter = self.growth_filter.currentData()
        from_date = self._date_value(self.date_from) if self.filter_enabled.isChecked() else None
        to_date = self._date_value(self.date_to) if self.filter_enabled.isChecked() else None
        if from_date and to_date and from_date > to_date:
            from_date, to_date = to_date, from_date

        entries: list[SanitaryDepartmentEntry] = []
        for department in departments:
            dep_name = str(department.name)
            if search and search not in dep_name.lower():
                continue

            dep_id = cast(int, department.id)
            samples = list(self.sanitary_service.list_samples_by_department(dep_id))
            filtered_samples = [
                sample
                for sample in samples
                if self._sample_matches_date_filter(sample, date_from=from_date, date_to=to_date)
            ]
            if not self._department_matches_growth_filter(filtered_samples, growth_filter):
                continue

            positive_count = sum(1 for sample in filtered_samples if sample.growth_flag == 1)
            pending_count = sum(1 for sample in filtered_samples if sample.growth_flag is None)
            entries.append(
                SanitaryDepartmentEntry(
                    dep_id=dep_id,
                    name=dep_name,
                    filtered_samples=filtered_samples,
                    total_count=len(filtered_samples),
                    positive_count=positive_count,
                    pending_count=pending_count,
                    last_sample=self._find_last_sample(filtered_samples),
                )
            )

        entries.sort(
            key=lambda entry: (
                entry.positive_count,
                entry.total_count,
                entry.last_sample is not None,
                entry.last_sample.taken_at if entry.last_sample is not None else None,
            ),
            reverse=True,
        )
        if not entries:
            return [], "filtered_out"
        return entries, None

    def _sample_matches_date_filter(
        self,
        sample: SanitarySampleResponse,
        *,
        date_from: date | None,
        date_to: date | None,
    ) -> bool:
        if date_from is None and date_to is None:
            return True
        if sample.taken_at is None:
            return False
        sample_date = sample.taken_at.date()
        if date_from is not None and sample_date < date_from:
            return False
        return not (date_to is not None and sample_date > date_to)

    def _department_matches_growth_filter(
        self,
        samples: list[SanitarySampleResponse],
        growth_filter: int | None,
    ) -> bool:
        if growth_filter is None:
            return True
        if growth_filter == 1:
            return any(sample.growth_flag == 1 for sample in samples)
        if growth_filter == 0:
            return any(sample.growth_flag == 0 for sample in samples)
        if growth_filter == -1:
            return any(sample.growth_flag is None for sample in samples)
        return True

    def _find_last_sample(self, samples: list[SanitarySampleResponse]) -> SanitarySampleResponse | None:
        taken_samples = [sample for sample in samples if sample.taken_at is not None]
        if not taken_samples:
            return None
        return max(taken_samples, key=lambda sample: cast(datetime, sample.taken_at))

    def _sample_taken_text(self, sample: SanitarySampleResponse | None) -> str:
        if sample is None or sample.taken_at is None:
            return "-"
        return sample.taken_at.strftime("%d.%m.%Y %H:%M")

    def _microbe_label(self, sample: SanitarySampleResponse) -> str:
        if sample.microorganism_id is not None:
            microbe = self._microbe_map.get(sample.microorganism_id)
            if microbe:
                return microbe
        return sample.microorganism_free or ""

    def _populate_list(self, entries: list[SanitaryDepartmentEntry], empty_state: str | None) -> None:
        updates_enabled = self.list_widget.updatesEnabled()
        self.list_widget.setUpdatesEnabled(False)
        self._list_item_widgets.clear()
        self.list_widget.clear()
        try:
            if empty_state == "no_data":
                self._add_empty_state(
                    "no_data",
                    "Проб пока нет",
                    "Санитарные пробы по отделениям ещё не зарегистрированы.",
                )
                return
            if empty_state == "filtered_out":
                self._add_empty_state(
                    "filtered_out",
                    "Ничего не найдено",
                    "Попробуйте изменить фильтры или сбросить текущие условия отбора.",
                )
                return

            self._last_empty_state = None
            for entry in entries:
                item = QListWidgetItem()
                card = self._build_department_item(entry)
                item.setData(Qt.ItemDataRole.UserRole, entry.dep_id)
                item.setData(Qt.ItemDataRole.UserRole + 1, entry.name)
                self._add_list_item_widget(item, card)
        finally:
            self.list_widget.setUpdatesEnabled(updates_enabled)

    def _add_empty_state(self, state: str, title: str, detail: str) -> None:
        self._last_empty_state = state
        item = QListWidgetItem()
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        card = self._build_empty_card(title, detail)
        self._add_list_item_widget(item, card)

    def _add_list_item_widget(self, item: QListWidgetItem, card: QWidget) -> None:
        hint = card.sizeHint().expandedTo(card.minimumSizeHint())
        item.setSizeHint(hint)
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, card)
        self._list_item_widgets.append(card)

    def _restore_selection(self, department_id: int | None) -> None:
        self._selected_department_id = None
        self._selected_department_name = ""
        if department_id is None:
            return
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item is None:
                continue
            if item.data(Qt.ItemDataRole.UserRole) == department_id:
                self.list_widget.setCurrentItem(item)
                self._selected_department_id = department_id
                self._selected_department_name = str(item.data(Qt.ItemDataRole.UserRole + 1) or "")
                return

    def _on_selection_changed(self) -> None:
        item = self.list_widget.currentItem()
        dep_id = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        dep_name = item.data(Qt.ItemDataRole.UserRole + 1) if item is not None else None
        self._selected_department_id = dep_id if isinstance(dep_id, int) else None
        self._selected_department_name = str(dep_name) if isinstance(dep_name, str) else ""
        self._update_selection_context()
        self._sync_action_state()

    def _sync_action_state(self) -> None:
        self._quick_open_button.setEnabled(self._selected_department_id is not None)

    def _handle_item_double_clicked(self, item: QListWidgetItem) -> None:
        self.list_widget.setCurrentItem(item)
        self._open_selected()

    def refresh(self) -> None:
        self._initial_refresh_pending = False
        previous_department_id = self._selected_department_id
        self._load_microbe_map()
        entries, empty_state = self._collect_entries()
        self._entries = entries
        self._update_filter_summary()
        self._update_kpis(entries)
        self.summary_label.setText(
            "Найдено "
            f"{len(entries)} отделений • проб {sum(entry.total_count for entry in entries)} • "
            f"положительных {sum(entry.positive_count for entry in entries)}"
        )

        blocker = QSignalBlocker(self.list_widget)
        self._populate_list(entries, empty_state)
        self._restore_selection(previous_department_id if empty_state is None else None)
        del blocker

        self._update_selection_context()
        self._sync_action_state()

    def refresh_references(self) -> None:
        self.refresh()
        self.references_updated.emit()

    def _open_selected(self) -> None:
        if self._selected_department_id is None:
            return
        dlg = SanitaryHistoryDialog(
            self.sanitary_service,
            self.reference_service,
            department_id=self._selected_department_id,
            department_name=self._selected_department_name,
            actor_id=self._session.user_id if self._session is not None else None,
            parent=self,
        )
        dlg.exec()
