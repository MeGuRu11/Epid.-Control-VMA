from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any, cast

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.services.lab_service import LabService
from app.application.services.reference_service import ReferenceService
from app.ui.lab.lab_sample_detail import LabSampleDetailDialog
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import show_warning
from app.ui.widgets.patient_selector import PatientSelector
from app.ui.widgets.responsive_actions import ResponsiveActionsPanel
from app.ui.widgets.table_utils import connect_combo_autowidth


class LabSamplesView(QWidget):
    references_updated = Signal()

    def __init__(
        self,
        lab_service: LabService,
        reference_service: ReferenceService,
        on_open_emz: Callable[[int | None, int | None], None] | None = None,
        on_data_changed: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.lab_service = lab_service
        self.reference_service = reference_service
        self.on_open_emz = on_open_emz
        self.on_data_changed = on_data_changed
        self.patient_id: int | None = None
        self.emr_case_id: int | None = None
        self._material_map: dict[int, str] = {}
        self._microbe_map: dict[int, str] = {}
        self._date_empty = QDate(2000, 1, 1)
        self.page_index = 1
        self.page_size = 50
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        title = QLabel("Лабораторные пробы пациента")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        quick_new = QPushButton("Новая проба")
        compact_button(quick_new)
        quick_new.clicked.connect(self._open_new_dialog)
        quick_save = QPushButton("Сохранить пробу")
        compact_button(quick_save)
        quick_save.clicked.connect(self._edit_selected)
        quick_open_patient = QPushButton("Открыть пациента")
        compact_button(quick_open_patient)
        quick_open_patient.clicked.connect(self._open_patient)
        self._quick_actions_panel = ResponsiveActionsPanel(min_button_width=132, max_columns=3)
        self._quick_actions_panel.set_buttons([quick_new, quick_save, quick_open_patient])
        self._quick_actions_panel.set_compact(self.width() < 1400)
        layout.addWidget(self._quick_actions_panel)

        header_row = QHBoxLayout()
        self.count_label = QLabel("Проб: 0")
        self.count_label.setObjectName("muted")
        header_row.addStretch()
        header_row.addWidget(self.count_label)
        layout.addLayout(header_row)

        self.filters_toggle = QPushButton("Показать фильтры ▸")
        compact_button(self.filters_toggle)
        self.filters_toggle.setCheckable(True)
        self.filters_toggle.toggled.connect(self._toggle_filters)
        layout.addWidget(self.filters_toggle)

        self.filter_box = QGroupBox("Фильтры")
        filter_layout = QGridLayout(self.filter_box)
        filter_layout.setHorizontalSpacing(10)
        filter_layout.setVerticalSpacing(6)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Номер пробы / часть номера")
        self.search_input.textChanged.connect(self._on_filter_changed)
        self.growth_filter = QComboBox()
        self.growth_filter.addItem("Все", None)
        self.growth_filter.addItem("Положительные", 1)
        self.growth_filter.addItem("Отрицательные", 0)
        connect_combo_autowidth(self.growth_filter)
        self.growth_filter.currentIndexChanged.connect(self._on_filter_changed)
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
        compact_button(clear_filters_btn)
        clear_filters_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(QLabel("Номер пробы"), 0, 0)
        filter_layout.addWidget(self.search_input, 0, 1)
        filter_layout.addWidget(QLabel("Рост"), 0, 2)
        filter_layout.addWidget(self.growth_filter, 0, 3)
        filter_layout.addWidget(QLabel("Материал"), 1, 0)
        filter_layout.addWidget(self.material_filter, 1, 1)
        filter_layout.addWidget(QLabel("Дата от"), 1, 2)
        filter_layout.addWidget(self.date_from, 1, 3)
        filter_layout.addWidget(QLabel("Дата до"), 1, 4)
        filter_layout.addWidget(self.date_to, 1, 5)
        filter_layout.addWidget(clear_filters_btn, 0, 5)
        self.filter_box.setVisible(False)
        layout.addWidget(self.filter_box)

        self.selector = PatientSelector(self._set_patient, parent=self)
        layout.addWidget(self.selector)

        list_box = QGroupBox("Список проб")
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

        layout.addStretch()
        self.refresh()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_quick_actions_panel"):
            self._quick_actions_panel.set_compact(self.width() < 1400)

    def _toggle_filters(self, checked: bool) -> None:
        self.filter_box.setVisible(checked)
        if checked:
            self.filters_toggle.setText("Скрыть фильтры ▾")
        else:
            self.filters_toggle.setText("Показать фильтры ▸")

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
        if sample.growth_flag == 1:
            status_tone = "danger"
        elif sample.growth_flag == 0:
            status_tone = "ok"
        else:
            status_tone = "warn"
        status_dot.setProperty("tone", status_tone)
        title = QLabel(f"{sample.lab_no} (id {sample.id})")
        title.setObjectName("cardTitle")
        header.addWidget(status_dot)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        taken_text = sample.taken_at.strftime("%d.%m.%Y %H:%M") if sample.taken_at else "-"
        growth_text = "Да" if sample.growth_flag == 1 else "Нет" if sample.growth_flag == 0 else "-"
        material_text = self._material_map.get(cast(int, sample.material_type_id), "-")
        micro_text = ""
        if sample.microorganism_id:
            micro_text = self._microbe_map.get(cast(int, sample.microorganism_id), "")
        if not micro_text and sample.microorganism_free:
            micro_text = sample.microorganism_free
        micro_part = f" · Микроорганизм: {micro_text}" if micro_text else ""
        location_part = f" · Локализация: {sample.material_location}" if sample.material_location else ""
        medium_part = f" · Среда: {sample.medium}" if sample.medium else ""
        meta = QLabel(
            f"Материал: {material_text} · Взято: {taken_text} · Рост: {growth_text}"
            f"{micro_part}{location_part}{medium_part}"
        )
        meta.setObjectName("cardMeta")
        layout.addWidget(meta)
        return wrapper

    def _open_new_dialog(self) -> None:
        if not self.patient_id:
            show_warning(self, "Выберите пациента или установите контекст.")
            return
        patient_id = cast(int, self.patient_id)
        dlg = LabSampleDetailDialog(
            self.lab_service,
            self.reference_service,
            patient_id,
            self.emr_case_id,
            parent=self,
        )
        self.references_updated.connect(dlg.refresh_references)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if self.on_data_changed:
                self.on_data_changed()
            self.refresh()
        self.references_updated.disconnect(dlg.refresh_references)

    def _edit_selected(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            show_warning(self, "Выберите пробу для сохранения.")
            return
        sample_id = cast(int, item.data(Qt.ItemDataRole.UserRole))
        patient_id = cast(int, self.patient_id)
        dlg = LabSampleDetailDialog(
            self.lab_service,
            self.reference_service,
            patient_id,
            self.emr_case_id,
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
        if not self.patient_id:
            self.count_label.setText("Проб: 0")
            self._add_empty_item("Выберите пациента для просмотра проб.")
            self._update_paging(0, 0)
            return
        self._load_material_map()
        self._load_microbe_map()
        samples = self.lab_service.list_samples(self.patient_id, self.emr_case_id)
        filtered = self._apply_filters(samples)
        filtered = sorted(
            filtered,
            key=lambda s: (s.taken_at is None, s.taken_at),
            reverse=True,
        )
        total = len(filtered)
        if not filtered:
            self.count_label.setText("Проб: 0")
            self._add_empty_item("Проб пока нет.")
            self._update_paging(0, 0)
            return
        page_items, start, end = self._paginate(filtered)
        for sample in page_items:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, sample.id)
            card = self._build_sample_item(sample)
            item.setSizeHint(card.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, card)
        self.count_label.setText(f"Проб: {total} (показано {start}-{end})")
        self._update_paging(total, len(page_items))

    def refresh_references(self) -> None:
        self.references_updated.emit()

    def _apply_filter(self) -> None:
        # kept for compatibility if needed
        self.refresh()

    def _set_patient(self, patient_id: int) -> None:
        self.patient_id = patient_id
        self._update_context_label()
        self.refresh()

    def _open_patient(self) -> None:
        if not self.patient_id:
            show_warning(self, "Сначала выберите пациента.")
            return
        if self.on_open_emz:
            self.on_open_emz(self.patient_id, self.emr_case_id)

    def set_context(self, patient_id: int | None, emr_case_id: int | None) -> None:
        if patient_id:
            self.patient_id = patient_id
            if hasattr(self.selector, "set_patient_id"):
                self.selector.set_patient_id(patient_id)
        else:
            self.patient_id = None
            if hasattr(self.selector, "clear"):
                self.selector.clear()
        self.emr_case_id = emr_case_id if patient_id else None
        self._update_context_label()
        self.refresh()

    def clear_context(self) -> None:
        self.set_context(None, None)

    def _update_context_label(self) -> None:
        self.count_label.setText("Проб: 0")

    def _load_material_map(self) -> None:
        self._material_map = {}
        materials = self.reference_service.list_material_types()
        current = self.material_filter.currentData()
        self.material_filter.blockSignals(True)
        self.material_filter.clear()
        self.material_filter.addItem("Все", None)
        for mt in materials:
            self._material_map[cast(int, mt.id)] = f"{mt.code} - {mt.name}"
            self.material_filter.addItem(self._material_map[cast(int, mt.id)], cast(int, mt.id))
        if current is not None:
            idx = self.material_filter.findData(current)
            if idx >= 0:
                self.material_filter.setCurrentIndex(idx)
        self.material_filter.blockSignals(False)

    def _load_microbe_map(self) -> None:
        self._microbe_map = {}
        for micro in self.reference_service.list_microorganisms():
            label = f"{micro.code or '-'} - {micro.name}"
            self._microbe_map[cast(int, micro.id)] = label

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
        self.material_filter.setCurrentIndex(0)
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

    def _date_value(self, widget: QDateEdit) -> date | None:
        qdate = widget.date()
        if qdate == self._date_empty:
            return None
        return cast(date, qdate.toPython())

    def _apply_filters(self, samples: list[Any]) -> list[Any]:
        search = self.search_input.text().strip().lower()
        growth = self.growth_filter.currentData()
        material_id = self.material_filter.currentData()
        date_from = self._date_value(self.date_from)
        date_to = self._date_value(self.date_to)
        filtered = []
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

    def _paginate(self, samples: list[Any]) -> tuple[list[Any], int, int]:
        total = len(samples)
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        if self.page_index > total_pages:
            self.page_index = total_pages
        if self.page_index < 1:
            self.page_index = 1
        start_idx = (self.page_index - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total)
        page_items = samples[start_idx:end_idx]
        start_label = start_idx + 1 if total > 0 else 0
        end_label = end_idx if total > 0 else 0
        return page_items, start_label, end_label
