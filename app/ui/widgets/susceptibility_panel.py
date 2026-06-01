from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.table_utils import (
    connect_combo_resize_on_content,
    resize_columns_to_content,
    set_combo_placeholder,
)


class _AntibioticsService(Protocol):
    def list_antibiotics(self) -> list[Any]: ...


class _PhagesService(Protocol):
    def list_phages(self) -> list[Any]: ...


@dataclass(frozen=True)
class SusceptibilityRow:
    """Сырая строка чувствительности, собранная из таблицы."""

    row_number: int
    antibiotic_id: int | None
    ris: str | None
    mic_text: str | None
    method: str | None


@dataclass(frozen=True)
class PhageRow:
    """Сырая строка панели фагов, собранная из таблицы."""

    row_number: int
    phage_id: int | None
    phage_free: str
    diameter_text: str | None


class SusceptibilityPanel(QWidget):
    """Общий редактор RIS/MIC и панели фагов для проб."""

    data_changed = Signal()

    def __init__(
        self,
        antibiotics_service: _AntibioticsService,
        phages_service: _PhagesService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.antibiotics_service = antibiotics_service
        self.phages_service = phages_service
        self._abx_list: list[Any] = []
        self._phage_list: list[Any] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.susc_table = self._make_table(["Антибиотик", "RIS", "MIC", "Метод"], 1)
        self.susc_table.setObjectName("susceptibilityTable")
        self._increase_table_height(self.susc_table)
        self.susc_table.itemChanged.connect(lambda _item: self.data_changed.emit())
        layout.addWidget(self.susc_table)

        susc_controls = QHBoxLayout()
        self.susc_add_btn = QPushButton("Добавить строку")
        compact_button(self.susc_add_btn)
        self.susc_add_btn.clicked.connect(self._add_susc_row)
        self.susc_del_btn = QPushButton("Удалить")
        compact_button(self.susc_del_btn)
        self.susc_del_btn.clicked.connect(lambda: self._delete_table_row(self.susc_table))
        self.template_btn = QPushButton("Заполнить шаблоны")
        compact_button(self.template_btn)
        self.template_btn.setToolTip("Заполнить RIS, метод и значения фагов по умолчанию для выбранных строк.")
        self.template_btn.clicked.connect(self.apply_default_templates)
        susc_controls.addWidget(self.susc_add_btn)
        susc_controls.addWidget(self.susc_del_btn)
        susc_controls.addWidget(self.template_btn)
        susc_controls.addStretch()
        layout.addLayout(susc_controls)

        self.phage_table = self._make_table(["Фаг", "Свободное имя", "Диаметр"], 1)
        self.phage_table.setObjectName("phageTable")
        self._increase_table_height(self.phage_table)
        self.phage_table.itemChanged.connect(lambda _item: self.data_changed.emit())
        layout.addWidget(self.phage_table)

        phage_controls = QHBoxLayout()
        self.phage_add_btn = QPushButton("Добавить строку")
        compact_button(self.phage_add_btn)
        self.phage_add_btn.clicked.connect(self._add_phage_row)
        self.phage_del_btn = QPushButton("Удалить")
        compact_button(self.phage_del_btn)
        self.phage_del_btn.clicked.connect(lambda: self._delete_table_row(self.phage_table))
        phage_controls.addWidget(self.phage_add_btn)
        phage_controls.addWidget(self.phage_del_btn)
        phage_controls.addStretch()
        layout.addLayout(phage_controls)

        self.refresh_references()

    def set_data(self, susceptibility_rows: list[Any], phage_rows: list[Any]) -> None:
        """Заполнить обе таблицы сохранёнными строками."""
        self.set_susceptibility_rows(susceptibility_rows)
        self.set_phage_rows(phage_rows)

    def set_susceptibility_rows(self, rows: list[Any]) -> None:
        """Заполнить таблицу чувствительности."""
        self.susc_table.clearContents()
        self.susc_table.setRowCount(max(len(rows), 1))
        self._setup_abx_rows()
        for idx, row in enumerate(rows):
            combo = cast(QComboBox | None, self.susc_table.cellWidget(idx, 0))
            if combo:
                combo.setCurrentIndex(combo.findData(_get_value(row, "antibiotic_id")))
            self.susc_table.setItem(idx, 1, QTableWidgetItem(str(_get_value(row, "ris") or "")))
            mic_value = _get_value(row, "mic_mg_l")
            self.susc_table.setItem(idx, 2, QTableWidgetItem(str(mic_value) if mic_value is not None else ""))
            self.susc_table.setItem(idx, 3, QTableWidgetItem(str(_get_value(row, "method") or "")))
        resize_columns_to_content(self.susc_table)

    def set_phage_rows(self, rows: list[Any]) -> None:
        """Заполнить таблицу фагов."""
        self.phage_table.clearContents()
        self.phage_table.setRowCount(max(len(rows), 1))
        self._setup_phage_rows()
        for idx, row in enumerate(rows):
            combo = cast(QComboBox | None, self.phage_table.cellWidget(idx, 0))
            if combo:
                combo.setCurrentIndex(combo.findData(_get_value(row, "phage_id")))
            self.phage_table.setItem(idx, 1, QTableWidgetItem(str(_get_value(row, "phage_free") or "")))
            diameter = _get_value(row, "lysis_diameter_mm")
            self.phage_table.setItem(idx, 2, QTableWidgetItem(str(diameter) if diameter is not None else ""))
        resize_columns_to_content(self.phage_table)

    def get_susceptibility_rows(self) -> list[SusceptibilityRow]:
        """Вернуть строки чувствительности в сервисно-независимом формате."""
        rows: list[SusceptibilityRow] = []
        for row in range(self.susc_table.rowCount()):
            abx_widget = self.susc_table.cellWidget(row, 0)
            abx_combo = cast(QComboBox, abx_widget) if isinstance(abx_widget, QComboBox) else None
            ris_item = self.susc_table.item(row, 1)
            mic_item = self.susc_table.item(row, 2)
            method_item = self.susc_table.item(row, 3)
            rows.append(
                SusceptibilityRow(
                    row_number=row + 1,
                    antibiotic_id=abx_combo.currentData() if abx_combo else None,
                    ris=ris_item.text() if ris_item else None,
                    mic_text=mic_item.text() if mic_item else None,
                    method=method_item.text() if method_item else None,
                )
            )
        return rows

    def get_phage_rows(self) -> list[PhageRow]:
        """Вернуть строки фагов в сервисно-независимом формате."""
        rows: list[PhageRow] = []
        for row in range(self.phage_table.rowCount()):
            ph_widget = self.phage_table.cellWidget(row, 0)
            ph_combo = cast(QComboBox, ph_widget) if isinstance(ph_widget, QComboBox) else None
            free_item = self.phage_table.item(row, 1)
            dia_item = self.phage_table.item(row, 2)
            rows.append(
                PhageRow(
                    row_number=row + 1,
                    phage_id=ph_combo.currentData() if ph_combo else None,
                    phage_free=free_item.text() if free_item else "",
                    diameter_text=dia_item.text() if dia_item else None,
                )
            )
        return rows

    def apply_default_templates(self) -> None:
        """Заполнить пустые значения шаблонами, не перетирая введённые данные."""
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

        resize_columns_to_content(self.susc_table)
        resize_columns_to_content(self.phage_table)
        self.data_changed.emit()

    def refresh_references(self) -> None:
        """Перезагрузить справочники, сохраняя выбранные значения."""
        selected_abx = [
            cast(QComboBox, widget).currentData() if (widget := self.susc_table.cellWidget(row, 0)) else None
            for row in range(self.susc_table.rowCount())
        ]
        selected_phages = [
            cast(QComboBox, widget).currentData() if (widget := self.phage_table.cellWidget(row, 0)) else None
            for row in range(self.phage_table.rowCount())
        ]
        self._refresh_abx_combos(selected_abx)
        self._refresh_phage_combos(selected_phages)

    def _setup_abx_rows(self) -> None:
        self._abx_list = self.antibiotics_service.list_antibiotics()
        for row in range(self.susc_table.rowCount()):
            combo = self._create_abx_combo()
            self.susc_table.setCellWidget(row, 0, combo)
            connect_combo_resize_on_content(self.susc_table, combo, row)
        resize_columns_to_content(self.susc_table)

    def _setup_phage_rows(self) -> None:
        self._phage_list = self.phages_service.list_phages()
        for row in range(self.phage_table.rowCount()):
            combo = self._create_phage_combo()
            self.phage_table.setCellWidget(row, 0, combo)
            connect_combo_resize_on_content(self.phage_table, combo, row)
        resize_columns_to_content(self.phage_table)

    def _refresh_abx_combos(self, selected_ids: list[int | None]) -> None:
        self._abx_list = self.antibiotics_service.list_antibiotics()
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
        self._phage_list = self.phages_service.list_phages()
        for row in range(self.phage_table.rowCount()):
            combo = self._create_phage_combo()
            if row < len(selected_ids) and selected_ids[row] is not None:
                idx = combo.findData(selected_ids[row])
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            self.phage_table.setCellWidget(row, 0, combo)
            connect_combo_resize_on_content(self.phage_table, combo, row)
        resize_columns_to_content(self.phage_table)

    def _create_abx_combo(self) -> QComboBox:
        combo = QComboBox()
        set_combo_placeholder(combo)
        for abx in self._abx_list:
            combo.addItem(f"{abx.code} - {abx.name}", abx.id)
        combo.setCurrentIndex(-1)
        combo.currentIndexChanged.connect(lambda _index: self.data_changed.emit())
        return combo

    def _create_phage_combo(self) -> QComboBox:
        combo = QComboBox()
        set_combo_placeholder(combo)
        for phage in self._phage_list:
            combo.addItem(f"{phage.code or '-'} - {phage.name}", phage.id)
        combo.setCurrentIndex(-1)
        combo.currentIndexChanged.connect(lambda _index: self.data_changed.emit())
        return combo

    def _add_susc_row(self) -> None:
        row = self.susc_table.rowCount()
        self.susc_table.insertRow(row)
        combo = self._create_abx_combo()
        self.susc_table.setCellWidget(row, 0, combo)
        connect_combo_resize_on_content(self.susc_table, combo, row)
        self.data_changed.emit()

    def _add_phage_row(self) -> None:
        row = self.phage_table.rowCount()
        self.phage_table.insertRow(row)
        combo = self._create_phage_combo()
        self.phage_table.setCellWidget(row, 0, combo)
        connect_combo_resize_on_content(self.phage_table, combo, row)
        self.data_changed.emit()

    def _delete_table_row(self, table: QTableWidget) -> None:
        if table.rowCount() <= 1:
            return
        row = table.currentRow()
        if row < 0:
            row = table.rowCount() - 1
        table.removeRow(row)
        self.data_changed.emit()

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
        return table

    def _increase_table_height(self, table: QTableWidget, multiplier: float = 0.8) -> None:
        base = max(table.sizeHint().height(), 220)
        table.setMinimumHeight(int(base * multiplier))


def _get_value(row: Any, name: str) -> Any:
    if isinstance(row, dict):
        return row.get(name)
    return getattr(row, name, None)
