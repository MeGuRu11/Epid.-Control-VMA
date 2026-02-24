from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol

from PySide6.QtCore import QDate, QDateTime
from PySide6.QtWidgets import QComboBox, QDateEdit, QDateTimeEdit


class IcdLike(Protocol):
    @property
    def code(self) -> object: ...

    @property
    def title(self) -> object: ...


class AntibioticLike(Protocol):
    @property
    def id(self) -> int: ...

    @property
    def code(self) -> object: ...

    @property
    def name(self) -> object: ...


class IsmpAbbreviationLike(Protocol):
    @property
    def code(self) -> object: ...

    @property
    def name(self) -> object: ...

    @property
    def description(self) -> object: ...


def create_diag_type_combo() -> QComboBox:
    combo = QComboBox()
    combo.addItems(["Поступление", "Перевод", "Выписка", "Осложнение"])
    return combo


def create_intervention_type_combo() -> QComboBox:
    combo = QComboBox()
    combo.setEditable(True)
    combo.addItems(
        [
            "Центральный катетер",
            "ИВЛ",
            "Дренаж",
            "Перевязка",
            "Операция",
            "Другое (введите вручную)",
        ]
    )
    combo.setCurrentText("")
    combo.setToolTip("Можно выбрать из списка или ввести вручную.")
    return combo


def create_datetime_cell(empty_dt: QDateTime) -> QDateTimeEdit:
    widget = QDateTimeEdit()
    widget.setCalendarPopup(True)
    widget.setDisplayFormat("dd.MM.yyyy HH:mm")
    widget.setMinimumDateTime(empty_dt)
    widget.setSpecialValueText("")
    widget.setDateTime(empty_dt)
    return widget


def create_date_cell(empty_date: QDate) -> QDateEdit:
    widget = QDateEdit()
    widget.setCalendarPopup(True)
    widget.setDisplayFormat("dd.MM.yyyy")
    widget.setMinimumDate(empty_date)
    widget.setDate(empty_date)
    widget.setSpecialValueText("")
    return widget


def create_icd_combo(*, icd_items: Sequence[IcdLike], wire_search: Callable[[QComboBox], None]) -> QComboBox:
    combo = QComboBox()
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    combo.addItem("Выбрать", None)
    for icd in icd_items:
        combo.addItem(f"{icd.code} - {icd.title}", str(icd.code))
    wire_search(combo)
    return combo


def populate_icd_combo(
    *,
    combo: QComboBox,
    icd_items: Sequence[IcdLike],
    selected_data: object | None,
    edit_text: str | None = None,
) -> None:
    combo.clear()
    combo.addItem("Выбрать", None)
    for icd in icd_items:
        combo.addItem(f"{icd.code} - {icd.title}", str(icd.code))
    if selected_data is not None:
        idx = combo.findData(selected_data)
        if idx >= 0:
            combo.setCurrentIndex(idx)
    if edit_text is not None:
        combo.setEditText(edit_text)


def create_abx_combo(*, antibiotics: Sequence[AntibioticLike]) -> QComboBox:
    combo = QComboBox()
    combo.addItem("Выбрать", None)
    for abx in antibiotics:
        combo.addItem(f"{abx.code} - {abx.name}", int(abx.id))
    return combo


def create_ismp_type_combo(
    *,
    abbreviations: Sequence[IsmpAbbreviationLike],
    tooltip_role: int,
) -> QComboBox:
    combo = QComboBox()
    combo.addItem("Выбрать", None)
    for item in abbreviations:
        code = str(item.code)
        name = str(item.name)
        label = f"{code} — {name}"
        combo.addItem(label, code)
        description = str(item.description or "")
        tooltip = description or name
        combo.setItemData(combo.count() - 1, tooltip, tooltip_role)
    return combo
