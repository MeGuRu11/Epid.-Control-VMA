from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import cast

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QDateEdit,
    QDialog,
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
from app.application.dto.lab_dto import LabSampleResponse
from app.application.services.lab_service import LabService
from app.application.services.reference_service import ReferenceService
from app.ui.lab.lab_sample_detail import LabSampleDetailDialog
from app.ui.widgets.action_bar_layout import update_action_bar_direction
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import show_warning
from app.ui.widgets.patient_selector import PatientSelector
from app.ui.widgets.table_utils import connect_combo_autowidth


@dataclass(frozen=True, slots=True)
class LabKpiSpec:
    key: str
    title: str
    badge: str
    detail: str
    tone: str


@dataclass(slots=True)
class LabKpiWidgets:
    value_label: QLabel
    detail_label: QLabel


LAB_KPI_SPECS = (
    LabKpiSpec("total", "Всего проб", "ALL", "в текущем контексте", "context"),
    LabKpiSpec("positive", "Положительный рост", "GR+", "с положительным ростом", "positive"),
    LabKpiSpec("negative", "Отрицательный рост", "GR-", "с отрицательным ростом", "negative"),
    LabKpiSpec("pending", "Без результата", "NR", "ожидают результата", "pending"),
)


class LabSamplesView(QWidget):
    references_updated = Signal()

    def __init__(
        self,
        lab_service: LabService,
        reference_service: ReferenceService,
        session: SessionContext | None = None,
        on_open_emz: Callable[[int | None, int | None], None] | None = None,
        on_data_changed: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.lab_service = lab_service
        self.reference_service = reference_service
        self._session = session
        self.on_open_emz = on_open_emz
        self.on_data_changed = on_data_changed
        self.patient_id: int | None = None
        self.emr_case_id: int | None = None
        self._material_map: dict[int, str] = {}
        self._microbe_map: dict[int, str] = {}
        self._kpi_widgets: dict[str, LabKpiWidgets] = {}
        self._kpi_cards: list[QWidget] = []
        self._kpi_columns = 1
        self._date_empty = QDate(2000, 1, 1)
        self._last_empty_state: str | None = None
        self.page_index = 1
        self.page_size = 50
        self._build_ui()

    def set_session(self, session: SessionContext) -> None:
        self._session = session

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setObjectName("labPageScrollArea")
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

        self._selector_card = self._build_selector_card()
        layout.addWidget(self._selector_card)

        self._filter_card = self._build_filter_card()
        layout.addWidget(self._filter_card)

        self._list_card = self._build_list_card()
        layout.addWidget(self._list_card, 1)

        self._apply_hero_layout()
        self._apply_filter_layout()
        self._reflow_utility_kpis()
        self._update_context_display()
        self._update_filter_summary()
        self._sync_action_state()
        self.refresh()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_quick_actions_layout()
        self._apply_hero_layout()
        self._apply_filter_layout()
        self._reflow_utility_kpis()

    def _build_hero_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("labHeroCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("Лаборатория")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel("Рабочая лента микробиологических проб по выбранному пациенту.")
        subtitle.setObjectName("labListMeta")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        context_grid = QGridLayout()
        context_grid.setContentsMargins(0, 0, 0, 0)
        context_grid.setHorizontalSpacing(12)
        context_grid.setVerticalSpacing(12)
        patient_card, self._patient_context_value = self._build_context_card("Пациент")
        case_card, self._case_context_value = self._build_context_card("Госпитализация")
        context_grid.addWidget(patient_card, 0, 0)
        context_grid.addWidget(case_card, 0, 1)
        context_grid.setColumnStretch(0, 1)
        context_grid.setColumnStretch(1, 1)
        layout.addLayout(context_grid)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(10)
        status_title = QLabel("Статус контекста")
        status_title.setObjectName("labContextTitle")
        self._context_badge = self._build_state_badge("", "warning")
        status_row.addWidget(status_title)
        status_row.addWidget(self._context_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        status_row.addStretch()
        layout.addLayout(status_row)

        self._quick_new_button = QPushButton("Новая проба")
        self._quick_new_button.setObjectName("primaryButton")
        compact_button(self._quick_new_button)
        self._quick_new_button.clicked.connect(self._open_new_dialog)

        self._quick_edit_button = QPushButton("Редактировать")
        self._quick_edit_button.setObjectName("secondaryButton")
        compact_button(self._quick_edit_button)
        self._quick_edit_button.clicked.connect(self._edit_selected)

        self._quick_open_patient_button = QPushButton("Открыть пациента")
        self._quick_open_patient_button.setObjectName("secondaryButton")
        compact_button(self._quick_open_patient_button)
        self._quick_open_patient_button.clicked.connect(self._open_patient)

        self._quick_actions_bar = QWidget()
        self._quick_actions_bar.setObjectName("sectionActionBar")
        self._quick_actions_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._quick_actions_bar)
        self._quick_actions_layout.setContentsMargins(12, 8, 12, 8)
        self._quick_actions_layout.setSpacing(10)

        self._quick_work_group = QWidget()
        self._quick_work_group.setObjectName("sectionActionGroup")
        work_layout = QHBoxLayout(self._quick_work_group)
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(8)
        work_layout.addWidget(self._quick_open_patient_button)
        work_layout.addWidget(self._quick_edit_button)

        self._quick_create_group = QWidget()
        self._quick_create_group.setObjectName("sectionActionGroup")
        create_layout = QHBoxLayout(self._quick_create_group)
        create_layout.setContentsMargins(0, 0, 0, 0)
        create_layout.addWidget(self._quick_new_button)

        self._quick_actions_layout.addWidget(self._quick_work_group)
        self._quick_actions_layout.addStretch()
        self._quick_actions_layout.addWidget(self._quick_create_group)
        layout.addWidget(self._quick_actions_bar)

        self._update_quick_actions_layout()
        return card

    def _build_utility_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("labUtilityCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Сводка по пробам")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self._utility_context_label = QLabel("Выберите пациента, чтобы увидеть сводку по пробам.")
        self._utility_context_label.setObjectName("labListMeta")
        self._utility_context_label.setWordWrap(True)
        layout.addWidget(self._utility_context_label)

        self._utility_grid = QGridLayout()
        self._utility_grid.setContentsMargins(0, 0, 0, 0)
        self._utility_grid.setHorizontalSpacing(12)
        self._utility_grid.setVerticalSpacing(12)
        for spec in LAB_KPI_SPECS:
            self._add_kpi_card(spec)
        layout.addLayout(self._utility_grid)
        layout.addStretch()
        return card

    def _build_selector_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("labListCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Выбор пациента")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        helper = QLabel("Укажите ID пациента или откройте встроенный поиск, затем работайте с текущим контекстом.")
        helper.setObjectName("labListMeta")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        self.selector = PatientSelector(self._set_patient, parent=self)
        layout.addWidget(self.selector)
        return card

    def _build_filter_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("labFilterCard")
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
        self._filter_summary_label.setObjectName("labListMeta")
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

        self._filter_content_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._filter_content_layout.setContentsMargins(0, 0, 0, 0)
        self._filter_content_layout.setSpacing(12)

        self._filter_primary_group = QWidget()
        primary_layout = QGridLayout(self._filter_primary_group)
        primary_layout.setContentsMargins(0, 0, 0, 0)
        primary_layout.setHorizontalSpacing(10)
        primary_layout.setVerticalSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Номер пробы / часть номера")
        self.search_input.textChanged.connect(self._on_filter_changed)

        self.growth_filter = QComboBox()
        self.growth_filter.addItem("Все", None)
        self.growth_filter.addItem("Положительный рост", 1)
        self.growth_filter.addItem("Отрицательный рост", 0)
        connect_combo_autowidth(self.growth_filter)
        self.growth_filter.currentIndexChanged.connect(self._on_filter_changed)

        primary_layout.addWidget(QLabel("Номер пробы"), 0, 0)
        primary_layout.addWidget(self.search_input, 0, 1)
        primary_layout.addWidget(QLabel("Рост"), 1, 0)
        primary_layout.addWidget(self.growth_filter, 1, 1)
        primary_layout.setColumnStretch(1, 1)

        self._filter_secondary_group = QWidget()
        secondary_layout = QGridLayout(self._filter_secondary_group)
        secondary_layout.setContentsMargins(0, 0, 0, 0)
        secondary_layout.setHorizontalSpacing(10)
        secondary_layout.setVerticalSpacing(8)

        self.material_filter = QComboBox()
        self.material_filter.addItem("Все", None)
        connect_combo_autowidth(self.material_filter)
        self.material_filter.currentIndexChanged.connect(self._on_filter_changed)

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

        clear_filters_btn = QPushButton("Сбросить")
        clear_filters_btn.setObjectName("secondaryButton")
        compact_button(clear_filters_btn)
        clear_filters_btn.clicked.connect(self._clear_filters)

        secondary_layout.addWidget(QLabel("Материал"), 0, 0)
        secondary_layout.addWidget(self.material_filter, 0, 1)
        secondary_layout.addWidget(QLabel("Дата от"), 1, 0)
        secondary_layout.addWidget(self.date_from, 1, 1)
        secondary_layout.addWidget(QLabel("Дата до"), 2, 0)
        secondary_layout.addWidget(self.date_to, 2, 1)
        secondary_layout.addWidget(clear_filters_btn, 3, 1, 1, 1, Qt.AlignmentFlag.AlignRight)
        secondary_layout.setColumnStretch(1, 1)

        self._filter_content_layout.addWidget(self._filter_primary_group, 1)
        self._filter_content_layout.addWidget(self._filter_secondary_group, 1)
        filter_wrapper.addLayout(self._filter_content_layout)
        layout.addWidget(self.filter_box)
        return card

    def _build_list_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("labListCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        card.setMinimumHeight(380)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Рабочая лента проб")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        self.count_label = QLabel("Контекст не выбран")
        self.count_label.setObjectName("labListMeta")
        toolbar.addWidget(self.count_label)
        toolbar.addStretch()

        page_size_title = QLabel("На странице")
        page_size_title.setObjectName("labListMeta")
        toolbar.addWidget(page_size_title)

        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["20", "50", "100"])
        self.page_size_combo.setCurrentText(str(self.page_size))
        connect_combo_autowidth(self.page_size_combo)
        self.page_size_combo.currentIndexChanged.connect(self._on_page_size_changed)
        toolbar.addWidget(self.page_size_combo)

        self.prev_btn = QPushButton("Назад")
        self.prev_btn.setObjectName("secondaryButton")
        compact_button(self.prev_btn)
        self.prev_btn.clicked.connect(self._prev_page)
        toolbar.addWidget(self.prev_btn)

        self.next_btn = QPushButton("Вперёд")
        self.next_btn.setObjectName("secondaryButton")
        compact_button(self.next_btn)
        self.next_btn.clicked.connect(self._next_page)
        toolbar.addWidget(self.next_btn)

        self.page_label = QLabel("Стр. 1 / 1")
        self.page_label.setObjectName("labListMeta")
        toolbar.addWidget(self.page_label)
        layout.addLayout(toolbar)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(8)
        self.list_widget.setMinimumHeight(240)
        self.list_widget.itemDoubleClicked.connect(self._edit_selected)
        self.list_widget.itemSelectionChanged.connect(self._sync_action_state)
        layout.addWidget(self.list_widget, 1)
        return card

    def _build_context_card(self, title: str) -> tuple[QWidget, QLabel]:
        card = QWidget()
        card.setObjectName("labContextCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("labContextTitle")
        value_label = QLabel("-")
        value_label.setObjectName("labContextValue")
        value_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card, value_label

    def _add_kpi_card(self, spec: LabKpiSpec) -> None:
        card = QWidget()
        card.setObjectName("labKpiCard")
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
        title_label.setObjectName("labKpiTitle")
        title_label.setWordWrap(True)
        top_row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        top_row.addWidget(title_label, 1)
        layout.addLayout(top_row)

        value_label = QLabel("0")
        value_label.setObjectName("labKpiValue")
        layout.addWidget(value_label)

        detail_label = QLabel(spec.detail)
        detail_label.setObjectName("labListMeta")
        detail_label.setWordWrap(True)
        layout.addWidget(detail_label)

        self._kpi_cards.append(card)
        self._kpi_widgets[spec.key] = LabKpiWidgets(value_label=value_label, detail_label=detail_label)

    def _build_state_badge(self, text: str, tone: str) -> QLabel:
        badge = QLabel(text)
        badge.setObjectName("labStateBadge")
        badge.setProperty("tone", tone)
        return badge

    def _build_sample_item(self, sample: LabSampleResponse) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("listCard")

        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QLabel(sample.lab_no or f"Проба #{sample.id}")
        title.setObjectName("cardTitle")
        sample_id = QLabel(f"id {sample.id}")
        sample_id.setObjectName("labListMeta")
        growth_text, growth_tone = self._growth_badge_data(sample.growth_flag)
        qc_text, qc_tone = self._qc_badge_data(sample.qc_status)
        growth_badge = self._build_state_badge(growth_text, growth_tone)
        qc_badge = self._build_state_badge(qc_text, qc_tone)

        header.addWidget(title)
        header.addWidget(sample_id)
        header.addStretch()
        header.addWidget(growth_badge)
        header.addWidget(qc_badge)
        layout.addLayout(header)

        material_text = self._material_map.get(sample.material_type_id, "-")
        taken_text = sample.taken_at.strftime("%d.%m.%Y %H:%M") if sample.taken_at else "Дата не указана"
        micro_text = self._microbe_label(sample)

        middle_parts = [
            f"Материал: {material_text}",
            f"Взято: {taken_text}",
            f"Микроорганизм: {micro_text or 'не указан'}",
        ]
        middle = QLabel(" • ".join(middle_parts))
        middle.setObjectName("labListMeta")
        middle.setWordWrap(True)
        layout.addWidget(middle)

        bottom_parts: list[str] = []
        if sample.material_location:
            bottom_parts.append(f"Локализация: {sample.material_location}")
        if sample.medium:
            bottom_parts.append(f"Среда: {sample.medium}")
        if sample.qc_due_at:
            bottom_parts.append(f"QC до: {sample.qc_due_at.strftime('%d.%m.%Y %H:%M')}")
        if not bottom_parts:
            bottom_parts.append("Дополнительных параметров пока нет")
        bottom = QLabel(" • ".join(bottom_parts))
        bottom.setObjectName("labListMeta")
        bottom.setWordWrap(True)
        layout.addWidget(bottom)
        return wrapper

    def _build_empty_card(self, title: str, detail: str) -> QWidget:
        card = QWidget()
        card.setObjectName("labEmptyCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        card.setMinimumHeight(112)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("labContextValue")
        detail_label = QLabel(detail)
        detail_label.setObjectName("labListMeta")
        detail_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(detail_label)
        layout.addStretch(1)
        return card

    def _microbe_label(self, sample: LabSampleResponse) -> str:
        if sample.microorganism_id is not None:
            microbe = self._microbe_map.get(sample.microorganism_id)
            if microbe:
                return microbe
        return sample.microorganism_free or ""

    def _growth_badge_data(self, growth_flag: int | None) -> tuple[str, str]:
        if growth_flag == 1:
            return "Рост +", "positive"
        if growth_flag == 0:
            return "Рост -", "negative"
        return "Без результата", "pending"

    def _qc_badge_data(self, qc_status: str | None) -> tuple[str, str]:
        if qc_status == "valid":
            return "QC валидно", "success"
        if qc_status == "conditional":
            return "QC условно", "warning"
        if qc_status == "rejected":
            return "QC отклонено", "error"
        return "QC ожидается", "pending"

    def _selected_sample_id(self) -> int | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        raw = item.data(Qt.ItemDataRole.UserRole)
        return raw if isinstance(raw, int) else None

    def _sync_action_state(self) -> None:
        has_patient = self.patient_id is not None
        self._quick_new_button.setEnabled(has_patient)
        self._quick_open_patient_button.setEnabled(has_patient)
        self._quick_edit_button.setEnabled(self._selected_sample_id() is not None)

    def _update_quick_actions_layout(self) -> None:
        available_width = max(0, self._scroll_area.viewport().width() - 48)
        if self._quick_actions_bar.width() > 0:
            available_width = min(available_width, self._quick_actions_bar.width())
        update_action_bar_direction(
            self._quick_actions_layout,
            self._quick_actions_bar,
            [self._quick_work_group, self._quick_create_group],
            extra_width=220,
            available_width=available_width,
        )

    def _apply_hero_layout(self) -> None:
        from app.ui.widgets.responsive import HERO_BREAKPOINT_PX, responsive_direction

        spacing = max(0, self._hero_layout.spacing())
        margins = self._hero_layout.contentsMargins()
        computed = (
            self._hero_card.minimumSizeHint().width()
            + self._utility_card.minimumSizeHint().width()
            + spacing
            + margins.left()
            + margins.right()
        )
        direction = responsive_direction(self.width(), computed, HERO_BREAKPOINT_PX)
        self._hero_layout.setDirection(direction)
        if direction == QBoxLayout.Direction.LeftToRight:
            self._hero_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._utility_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        else:
            self._hero_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self._utility_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._hero_card.updateGeometry()
        self._utility_card.updateGeometry()

    def _apply_filter_layout(self) -> None:
        from app.ui.widgets.responsive import FILTER_BREAKPOINT_PX, responsive_direction

        spacing = max(0, self._filter_content_layout.spacing())
        margins = self._filter_content_layout.contentsMargins()
        computed = (
            self._filter_primary_group.minimumSizeHint().width()
            + self._filter_secondary_group.minimumSizeHint().width()
            + spacing
            + margins.left()
            + margins.right()
            + 80
        )
        available_width = max(0, self._scroll_area.viewport().width() - 32)
        direction = responsive_direction(available_width, computed, FILTER_BREAKPOINT_PX)
        self._filter_content_layout.setDirection(direction)
        self._filter_primary_group.updateGeometry()
        self._filter_secondary_group.updateGeometry()

    def _reflow_utility_kpis(self) -> None:
        while self._utility_grid.count():
            item = self._utility_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(self._utility_card)

        if not self._kpi_cards:
            self._kpi_columns = 1
            return

        card_min_width = max(card.minimumSizeHint().width() for card in self._kpi_cards)
        spacing = max(0, self._utility_grid.horizontalSpacing())
        margins = self._utility_grid.contentsMargins()
        required_width = card_min_width * 2 + spacing + margins.left() + margins.right()
        columns = 2 if self._utility_card.width() >= required_width else 1
        self._kpi_columns = columns

        for idx, card in enumerate(self._kpi_cards):
            row = idx // columns
            column = idx % columns
            self._utility_grid.addWidget(card, row, column)
        self._utility_grid.setColumnStretch(0, 1)
        self._utility_grid.setColumnStretch(1, 1 if columns == 2 else 0)

    def _toggle_filters(self, checked: bool) -> None:
        self.filter_box.setVisible(checked)
        self.filters_toggle.setText("Скрыть фильтры" if checked else "Показать фильтры")

    def _update_context_display(self) -> None:
        if self.patient_id is None:
            self._patient_context_value.setText("Не выбран")
            self._case_context_value.setText("Не выбрана")
            self._utility_context_label.setText("Выберите пациента, чтобы увидеть сводку по пробам.")
            self._set_context_badge("Нужен пациент", "warning")
            return

        self._patient_context_value.setText(f"Пациент #{self.patient_id}")
        if self.emr_case_id is None:
            self._case_context_value.setText("Не выбрана")
            self._utility_context_label.setText(f"Текущий контекст: пациент #{self.patient_id}.")
        else:
            self._case_context_value.setText(f"ЭМЗ #{self.emr_case_id}")
            self._utility_context_label.setText(
                f"Текущий контекст: пациент #{self.patient_id}, госпитализация #{self.emr_case_id}."
            )
        self._set_context_badge("Контекст выбран", "success")

    def _set_context_badge(self, text: str, tone: str) -> None:
        self._context_badge.setText(text)
        self._context_badge.setProperty("tone", tone)
        style = self._context_badge.style()
        style.unpolish(self._context_badge)
        style.polish(self._context_badge)
        self._context_badge.update()

    def _update_kpis(self, samples: list[LabSampleResponse] | None) -> None:
        if samples is None:
            for spec in LAB_KPI_SPECS:
                widgets = self._kpi_widgets[spec.key]
                widgets.value_label.setText("0")
                widgets.detail_label.setText("Выберите пациента")
            return

        positive_count = sum(1 for sample in samples if sample.growth_flag == 1)
        negative_count = sum(1 for sample in samples if sample.growth_flag == 0)
        pending_count = sum(1 for sample in samples if sample.growth_flag is None)
        values = {
            "total": len(samples),
            "positive": positive_count,
            "negative": negative_count,
            "pending": pending_count,
        }
        for spec in LAB_KPI_SPECS:
            widgets = self._kpi_widgets[spec.key]
            widgets.value_label.setText(str(values[spec.key]))
            widgets.detail_label.setText(spec.detail)

    def _active_filter_summary_parts(self) -> list[str]:
        parts: list[str] = []
        search = self.search_input.text().strip()
        if search:
            parts.append(f"№: {search}")

        growth = self.growth_filter.currentData()
        if growth == 1:
            parts.append("рост: положительный")
        elif growth == 0:
            parts.append("рост: отрицательный")

        material_id = self.material_filter.currentData()
        if material_id is not None:
            parts.append(f"материал: {self.material_filter.currentText()}")

        date_from = self._date_value(self.date_from)
        if date_from is not None:
            parts.append(f"от: {date_from.strftime('%d.%m.%Y')}")

        date_to = self._date_value(self.date_to)
        if date_to is not None:
            parts.append(f"до: {date_to.strftime('%d.%m.%Y')}")
        return parts

    def _update_filter_summary(self) -> None:
        parts = self._active_filter_summary_parts()
        self._filter_summary_label.setText(" • ".join(parts) if parts else "Без фильтров")

    def _has_active_filters(self) -> bool:
        return bool(self._active_filter_summary_parts())

    def _list_summary_text(self, total_samples: int, filtered_total: int, start: int, end: int) -> str:
        if filtered_total == 0:
            if total_samples == 0:
                return "В текущем контексте пока нет проб"
            return f"Найдено 0 из {total_samples}"
        if filtered_total != total_samples:
            return f"Найдено {filtered_total} из {total_samples} • показано {start}-{end}"
        return f"Всего {filtered_total} • показано {start}-{end}"

    def _open_new_dialog(self) -> None:
        if self.patient_id is None:
            show_warning(self, "Выберите пациента или установите контекст.")
            return
        dlg = LabSampleDetailDialog(
            self.lab_service,
            self.reference_service,
            self.patient_id,
            self.emr_case_id,
            actor_id=self._session.user_id if self._session is not None else None,
            parent=self,
        )
        self.references_updated.connect(dlg.refresh_references)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if self.on_data_changed:
                self.on_data_changed()
            self.refresh()
        self.references_updated.disconnect(dlg.refresh_references)

    def _edit_selected(self, _item: QListWidgetItem | None = None) -> None:
        sample_id = self._selected_sample_id()
        if sample_id is None:
            show_warning(self, "Выберите пробу для редактирования.")
            return
        if self.patient_id is None:
            show_warning(self, "Сначала выберите пациента.")
            return
        dlg = LabSampleDetailDialog(
            self.lab_service,
            self.reference_service,
            self.patient_id,
            self.emr_case_id,
            actor_id=self._session.user_id if self._session is not None else None,
            sample_id=sample_id,
            parent=self,
        )
        self.references_updated.connect(dlg.refresh_references)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if self.on_data_changed:
                self.on_data_changed()
            self.refresh()
        self.references_updated.disconnect(dlg.refresh_references)

    def refresh(self) -> None:
        self.list_widget.clear()
        self._last_empty_state = None
        self._update_context_display()
        self._update_filter_summary()

        if self.patient_id is None:
            self._update_kpis(None)
            self.count_label.setText("Контекст не выбран")
            self._add_empty_state(
                "Выберите пациента",
                "Сначала установите пациентский контекст, чтобы увидеть лабораторные пробы и сводку.",
                empty_state="no_context",
            )
            self._update_paging(0)
            self._sync_action_state()
            return

        self._load_material_map()
        self._load_microbe_map()
        self._update_filter_summary()

        samples = self.lab_service.list_samples(self.patient_id, self.emr_case_id)
        self._update_kpis(samples)
        filtered_samples = sorted(
            self._apply_filters(samples),
            key=lambda sample: (sample.taken_at is None, sample.taken_at),
            reverse=True,
        )

        if not samples:
            self.count_label.setText("В текущем контексте 0 проб")
            self._add_empty_state(
                "Проб пока нет",
                "Для выбранного пациента ещё не зарегистрированы лабораторные пробы.",
                empty_state="no_data",
            )
            self._update_paging(0)
            self._sync_action_state()
            return

        if not filtered_samples:
            self.count_label.setText(f"Найдено 0 из {len(samples)}")
            self._add_empty_state(
                "Ничего не найдено",
                "Попробуйте смягчить условия поиска или сбросить активные фильтры.",
                empty_state="filtered_out",
            )
            self._update_paging(0)
            self._sync_action_state()
            return

        page_items, start, end = self._paginate(filtered_samples)
        for sample in page_items:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, sample.id)
            card = self._build_sample_item(sample)
            item.setSizeHint(card.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, card)

        self.count_label.setText(self._list_summary_text(len(samples), len(filtered_samples), start, end))
        self._update_paging(len(filtered_samples))
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
        self._sync_action_state()

    def refresh_references(self) -> None:
        self.references_updated.emit()

    def _apply_filter(self) -> None:
        self.refresh()

    def _set_patient(self, patient_id: int) -> None:
        self.patient_id = patient_id
        self._update_context_display()
        self.refresh()

    def _open_patient(self) -> None:
        if self.patient_id is None:
            show_warning(self, "Сначала выберите пациента.")
            return
        if self.on_open_emz:
            self.on_open_emz(self.patient_id, self.emr_case_id)

    def set_context(self, patient_id: int | None, emr_case_id: int | None) -> None:
        if patient_id is not None:
            self.patient_id = patient_id
            if hasattr(self.selector, "set_patient_id"):
                self.selector.set_patient_id(patient_id)
        else:
            self.patient_id = None
            if hasattr(self.selector, "clear"):
                self.selector.clear()
        self.emr_case_id = emr_case_id if patient_id is not None else None
        self._update_context_display()
        self.refresh()

    def clear_context(self) -> None:
        self.set_context(None, None)

    def _load_material_map(self) -> None:
        self._material_map = {}
        materials = self.reference_service.list_material_types()
        current = self.material_filter.currentData()
        self.material_filter.blockSignals(True)
        self.material_filter.clear()
        self.material_filter.addItem("Все", None)
        for material in materials:
            self._material_map[cast(int, material.id)] = f"{material.code} — {material.name}"
            self.material_filter.addItem(self._material_map[cast(int, material.id)], cast(int, material.id))
        if current is not None:
            index = self.material_filter.findData(current)
            if index >= 0:
                self.material_filter.setCurrentIndex(index)
        self.material_filter.blockSignals(False)

    def _load_microbe_map(self) -> None:
        self._microbe_map = {}
        for microorganism in self.reference_service.list_microorganisms():
            self._microbe_map[cast(int, microorganism.id)] = f"{microorganism.code or '-'} — {microorganism.name}"

    def _add_empty_state(self, title: str, detail: str, *, empty_state: str) -> None:
        self._last_empty_state = empty_state
        item = QListWidgetItem()
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        card = self._build_empty_card(title, detail)
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, card)
        hint = card.sizeHint().expandedTo(card.minimumSizeHint())
        hint.setHeight(max(hint.height(), card.minimumHeight()))
        item.setSizeHint(hint)

    def _on_filter_changed(self) -> None:
        self.page_index = 1
        self._update_filter_summary()
        self.refresh()

    def _clear_filters(self) -> None:
        self.search_input.clear()
        self.growth_filter.setCurrentIndex(0)
        self.material_filter.setCurrentIndex(0)
        self.date_from.setDate(self._date_empty)
        self.date_to.setDate(self._date_empty)
        self.page_index = 1
        self._update_filter_summary()
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

    def _update_paging(self, total: int) -> None:
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        if self.page_index > total_pages:
            self.page_index = total_pages
        if total == 0:
            self.page_label.setText("Стр. 1 / 1")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return
        self.page_label.setText(f"Стр. {self.page_index} / {total_pages}")
        self.prev_btn.setEnabled(self.page_index > 1)
        self.next_btn.setEnabled(self.page_index < total_pages)

    def _date_value(self, widget: QDateEdit) -> date | None:
        qdate = widget.date()
        if qdate == self._date_empty:
            return None
        return cast(date, qdate.toPython())

    def _apply_filters(self, samples: list[LabSampleResponse]) -> list[LabSampleResponse]:
        search = self.search_input.text().strip().lower()
        growth = self.growth_filter.currentData()
        material_id = self.material_filter.currentData()
        date_from = self._date_value(self.date_from)
        date_to = self._date_value(self.date_to)
        filtered: list[LabSampleResponse] = []
        for sample in samples:
            if search and search not in (sample.lab_no or "").lower():
                continue
            if growth is not None and sample.growth_flag != growth:
                continue
            if material_id is not None and sample.material_type_id != material_id:
                continue
            taken = sample.taken_at.date() if sample.taken_at else None
            if date_from and (taken is None or taken < date_from):
                continue
            if date_to and (taken is None or taken > date_to):
                continue
            filtered.append(sample)
        return filtered

    def _paginate(self, samples: list[LabSampleResponse]) -> tuple[list[LabSampleResponse], int, int]:
        total = len(samples)
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        if self.page_index > total_pages:
            self.page_index = total_pages
        if self.page_index < 1:
            self.page_index = 1
        start_index = (self.page_index - 1) * self.page_size
        end_index = min(start_index + self.page_size, total)
        page_items = samples[start_index:end_index]
        start_label = start_index + 1 if total > 0 else 0
        end_label = end_index if total > 0 else 0
        return page_items, start_label, end_label
