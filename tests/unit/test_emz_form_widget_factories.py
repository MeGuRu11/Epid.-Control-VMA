from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from PySide6.QtCore import QDate, QDateTime, QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QComboBox

import app.ui.emz.form_widget_factories as factories


class _InsertPolicy:
    NoInsert = 1


class _FakeComboBox:
    InsertPolicy = _InsertPolicy

    def __init__(self) -> None:
        self.editable = False
        self.insert_policy: int | None = None
        self.items: list[tuple[str, object]] = []
        self.item_data: dict[tuple[int, int], object] = {}
        self.current_text = ""
        self.tooltip = ""
        self.current_index = -1
        self.edit_text = ""
        self.max_visible_items: int | None = None
        self.popup_view = _FakePopupView()

    def setEditable(self, editable: bool) -> None:  # noqa: N802
        self.editable = editable

    def setInsertPolicy(self, policy: int) -> None:  # noqa: N802
        self.insert_policy = policy

    def setMaxVisibleItems(self, count: int) -> None:  # noqa: N802
        self.max_visible_items = count

    def view(self) -> _FakePopupView:
        return self.popup_view

    def addItem(self, label: str, data: object = None) -> None:  # noqa: N802
        self.items.append((label, data))

    def addItems(self, labels: list[str]) -> None:  # noqa: N802
        for label in labels:
            self.addItem(label, label)

    def clear(self) -> None:
        self.items.clear()
        self.current_index = -1

    def findData(self, data: object) -> int:  # noqa: N802
        for idx, (_, item_data) in enumerate(self.items):
            if item_data == data:
                return idx
        return -1

    def setCurrentIndex(self, idx: int) -> None:  # noqa: N802
        self.current_index = idx

    def setCurrentText(self, value: str) -> None:  # noqa: N802
        self.current_text = value

    def setToolTip(self, value: str) -> None:  # noqa: N802
        self.tooltip = value

    def setEditText(self, value: str) -> None:  # noqa: N802
        self.edit_text = value

    def count(self) -> int:
        return len(self.items)

    def setItemData(self, idx: int, value: object, role: int) -> None:  # noqa: N802
        self.item_data[(idx, role)] = value


class _FakePopupView:
    def __init__(self) -> None:
        self.maximum_height: int | None = None

    def setMaximumHeight(self, value: int) -> None:  # noqa: N802
        self.maximum_height = value


class _FakeDateTimeEdit:
    def __init__(self) -> None:
        self.calendar_popup = False
        self.display_format = ""
        self.minimum_dt: object | None = None
        self.special_text: str | None = None
        self.current_dt: object | None = None

    def setCalendarPopup(self, enabled: bool) -> None:  # noqa: N802
        self.calendar_popup = enabled

    def setDisplayFormat(self, value: str) -> None:  # noqa: N802
        self.display_format = value

    def setMinimumDateTime(self, value: object) -> None:  # noqa: N802
        self.minimum_dt = value

    def setSpecialValueText(self, value: str) -> None:  # noqa: N802
        self.special_text = value

    def setDateTime(self, value: object) -> None:  # noqa: N802
        self.current_dt = value


class _FakeDateEdit:
    def __init__(self) -> None:
        self.calendar_popup = False
        self.display_format = ""
        self.minimum_date: object | None = None
        self.current_date: object | None = None
        self.special_text: str | None = None

    def setCalendarPopup(self, enabled: bool) -> None:  # noqa: N802
        self.calendar_popup = enabled

    def setDisplayFormat(self, value: str) -> None:  # noqa: N802
        self.display_format = value

    def setMinimumDate(self, value: object) -> None:  # noqa: N802
        self.minimum_date = value

    def setDate(self, value: object) -> None:  # noqa: N802
        self.current_date = value

    def setSpecialValueText(self, value: str) -> None:  # noqa: N802
        self.special_text = value


@dataclass(frozen=True)
class _Icd:
    code: str
    title: str


@dataclass(frozen=True)
class _Abx:
    id: int
    code: str
    name: str


@dataclass(frozen=True)
class _Ismp:
    code: str
    name: str
    description: str | None = None


def test_create_diag_type_combo(monkeypatch) -> None:
    monkeypatch.setattr(factories, "QComboBox", _FakeComboBox)
    combo = cast(_FakeComboBox, factories.create_diag_type_combo())
    assert len(combo.items) == 4
    assert all(label for label, _ in combo.items)


def test_create_intervention_type_combo(monkeypatch) -> None:
    monkeypatch.setattr(factories, "QComboBox", _FakeComboBox)
    combo = cast(_FakeComboBox, factories.create_intervention_type_combo())
    assert combo.editable is True
    assert combo.current_text == ""
    assert combo.tooltip != ""
    assert len(combo.items) == 6


def test_create_datetime_cell(monkeypatch) -> None:
    monkeypatch.setattr(factories, "QDateTimeEdit", _FakeDateTimeEdit)
    marker = cast(QDateTime, object())
    widget = cast(_FakeDateTimeEdit, factories.create_datetime_cell(marker))
    assert widget.calendar_popup is True
    assert widget.display_format == "dd.MM.yyyy HH:mm"
    assert widget.minimum_dt is marker
    assert widget.current_dt is marker
    assert widget.special_text == ""


def test_create_date_cell(monkeypatch) -> None:
    monkeypatch.setattr(factories, "QDateEdit", _FakeDateEdit)
    marker = cast(QDate, object())
    widget = cast(_FakeDateEdit, factories.create_date_cell(marker))
    assert widget.calendar_popup is True
    assert widget.display_format == "dd.MM.yyyy"
    assert widget.minimum_date is marker
    assert widget.current_date is marker
    assert widget.special_text == ""


def test_create_icd_combo_and_wire(monkeypatch) -> None:
    monkeypatch.setattr(factories, "QComboBox", _FakeComboBox)
    wired: list[object] = []

    def _wire(combo: QComboBox) -> None:
        wired.append(combo)

    combo = cast(
        _FakeComboBox,
        factories.create_icd_combo(
            icd_items=[_Icd(code="A00", title="Cholera")],
            wire_search=cast(Callable[[QComboBox], None], _wire),
        ),
    )
    assert combo.editable is True
    assert combo.insert_policy == _InsertPolicy.NoInsert
    assert combo.items[0][1] is None
    assert combo.items[1] == ("A00 - Cholera", "A00")
    assert wired == [combo]


def test_populate_icd_combo_restores_selection_and_edit_text(monkeypatch) -> None:
    monkeypatch.setattr(factories, "QComboBox", _FakeComboBox)
    combo = _FakeComboBox()
    factories.populate_icd_combo(
        combo=cast(QComboBox, combo),
        icd_items=[_Icd(code="A00", title="Cholera"), _Icd(code="B00", title="Herpes")],
        selected_data="B00",
        edit_text="Her",
    )
    assert combo.items[0][1] is None
    assert combo.current_index == 2
    assert combo.edit_text == "Her"


def test_create_abx_combo(qapp) -> None:
    combo = factories.create_abx_combo(antibiotics=[_Abx(id=5, code="ABX", name="Amoxicillin")])

    assert combo.itemData(0) is None
    assert combo.itemText(1) == "ABX - Amoxicillin"
    assert combo.itemData(1) == 5
    assert combo.maxVisibleItems() == factories.ABX_COMBO_MAX_VISIBLE_ITEMS
    assert combo.view().maximumHeight() == factories.ABX_COMBO_POPUP_MAX_HEIGHT

    combo.close()


def test_create_abx_combo_limits_real_popup_container_height(qapp) -> None:
    combo = factories.create_abx_combo(
        antibiotics=[_Abx(id=idx, code=f"ABX-{idx:04d}", name="Antibiotic") for idx in range(1, 61)]
    )
    combo.show()
    qapp.processEvents()

    combo.showPopup()
    qapp.processEvents()

    assert isinstance(combo, factories.LimitedPopupComboBox)
    popup = combo._popup_frame
    popup_view = combo._popup_view
    assert popup is not None
    assert popup_view is not None
    assert combo._global_wheel_filter_installed is True
    assert popup.height() == factories.ABX_COMBO_POPUP_MAX_HEIGHT
    assert popup.mapToGlobal(QPoint(0, 0)).y() >= combo.mapToGlobal(QPoint(0, combo.height())).y()
    scrollbar = popup_view.verticalScrollBar()
    assert scrollbar.maximum() > 0
    assert isinstance(popup_view, factories.AntibioticPopupListView)
    start_value = scrollbar.value()
    wheel = QWheelEvent(
        QPointF(8, 8),
        QPointF(popup_view.mapToGlobal(QPoint(8, 8))),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )
    assert combo.eventFilter(popup_view.viewport(), wheel) is True
    assert scrollbar.value() > start_value

    combo.hidePopup()
    assert combo._global_wheel_filter_installed is False
    combo.close()


def test_create_ismp_type_combo_sets_tooltip(monkeypatch) -> None:
    monkeypatch.setattr(factories, "QComboBox", _FakeComboBox)
    combo = cast(
        _FakeComboBox,
        factories.create_ismp_type_combo(
            abbreviations=[_Ismp(code="VAP", name="Pneumonia", description=None)],
            tooltip_role=42,
        ),
    )
    assert combo.items[0][1] is None
    assert combo.items[1][0].startswith("VAP")
    assert combo.items[1][1] == "VAP"
    assert combo.item_data[(1, 42)] == "Pneumonia"
