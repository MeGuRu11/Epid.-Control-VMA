from __future__ import annotations

from typing import cast

from PySide6.QtWidgets import QTableWidget

import app.ui.emz.form_table_setups as setups


class _FakeCombo:
    def __init__(self, data_to_index: dict[object, int] | None = None) -> None:
        self._data_to_index = data_to_index or {}
        self._index_to_data = {index: data for data, index in self._data_to_index.items()}
        self.current_text = ""
        self.current_index = -1

    def setCurrentText(self, value: str) -> None:  # noqa: N802
        self.current_text = value

    def currentText(self) -> str:  # noqa: N802
        return self.current_text

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        self.current_index = index

    def findData(self, value: object) -> int:  # noqa: N802
        return self._data_to_index.get(value, -1)

    def currentData(self) -> object | None:  # noqa: N802
        return self._index_to_data.get(self.current_index)


class _FakeDateTimeEdit:
    pass


class _FakeDateEdit:
    pass


class _FakeTable:
    def __init__(self, row_count: int = 0) -> None:
        self._row_count = row_count
        self.widgets: dict[tuple[int, int], object] = {}

    def rowCount(self) -> int:  # noqa: N802
        return self._row_count

    def cellWidget(self, row: int, col: int) -> object | None:  # noqa: N802
        return self.widgets.get((row, col))

    def setCellWidget(self, row: int, col: int, widget: object) -> None:  # noqa: N802
        self.widgets[(row, col)] = widget


def test_setup_diagnosis_rows_creates_combos_and_resizes(monkeypatch) -> None:
    connect_rows: list[int] = []
    resize_calls: list[int] = []

    def fake_connect(_table: QTableWidget, _combo: _FakeCombo, row: int) -> None:
        connect_rows.append(row)

    monkeypatch.setattr(setups, "connect_combo_resize_on_first_row", fake_connect)

    table = cast(QTableWidget, _FakeTable(row_count=2))

    setups.setup_diagnosis_rows(
        table=table,
        create_type_combo=cast(setups.CreateComboFn, lambda: _FakeCombo()),
        create_icd_combo=cast(setups.CreateComboFn, lambda: _FakeCombo()),
        resize_table=lambda _table: resize_calls.append(1),
    )

    fake = cast(_FakeTable, table)
    assert isinstance(fake.cellWidget(0, 0), _FakeCombo)
    assert isinstance(fake.cellWidget(0, 1), _FakeCombo)
    assert isinstance(fake.cellWidget(1, 0), _FakeCombo)
    assert isinstance(fake.cellWidget(1, 1), _FakeCombo)
    assert connect_rows == [0, 0, 1, 1]
    assert len(resize_calls) == 1


def test_setup_abx_rows_preserves_existing_datetime_widget(monkeypatch) -> None:
    monkeypatch.setattr(setups, "QDateTimeEdit", _FakeDateTimeEdit)
    connect_rows: list[int] = []

    def fake_connect(_table: QTableWidget, _combo: _FakeCombo, row: int) -> None:
        connect_rows.append(row)

    monkeypatch.setattr(setups, "connect_combo_resize_on_first_row", fake_connect)

    table = cast(QTableWidget, _FakeTable(row_count=1))
    existing_start = _FakeDateTimeEdit()
    cast(_FakeTable, table).setCellWidget(0, 0, existing_start)

    setups.setup_abx_rows(
        table=table,
        create_dt_cell=cast(setups.CreateDateTimeEditFn, lambda: _FakeDateTimeEdit()),
        create_abx_combo=cast(setups.CreateComboFn, lambda: _FakeCombo()),
        resize_table=lambda _table: None,
    )

    fake = cast(_FakeTable, table)
    assert fake.cellWidget(0, 0) is existing_start
    assert isinstance(fake.cellWidget(0, 1), _FakeDateTimeEdit)
    assert isinstance(fake.cellWidget(0, 2), _FakeCombo)
    assert connect_rows == [0]


def test_refresh_diagnosis_reference_rows_preserves_selected_values(monkeypatch) -> None:
    monkeypatch.setattr(setups, "QComboBox", _FakeCombo)
    connect_rows: list[int] = []

    def fake_connect(_table: QTableWidget, _combo: _FakeCombo, row: int) -> None:
        connect_rows.append(row)

    monkeypatch.setattr(setups, "connect_combo_resize_on_first_row", fake_connect)

    table = cast(QTableWidget, _FakeTable(row_count=1))
    old_type_combo = _FakeCombo()
    old_type_combo.setCurrentText("Выписка")
    old_icd_combo = _FakeCombo({"A00": 1})
    old_icd_combo.setCurrentIndex(1)
    fake = cast(_FakeTable, table)
    fake.setCellWidget(0, 0, old_type_combo)
    fake.setCellWidget(0, 1, old_icd_combo)

    setups.refresh_diagnosis_reference_rows(
        table=table,
        create_type_combo=cast(setups.CreateComboFn, lambda: _FakeCombo()),
        create_icd_combo=cast(setups.CreateComboFn, lambda: _FakeCombo({"A00": 4})),
    )

    new_type_combo = cast(_FakeCombo, fake.cellWidget(0, 0))
    new_icd_combo = cast(_FakeCombo, fake.cellWidget(0, 1))
    assert new_type_combo.current_text == "Выписка"
    assert new_icd_combo.current_index == 4
    assert connect_rows == [0, 0]


def test_refresh_abx_reference_rows_preserves_selected_value(monkeypatch) -> None:
    monkeypatch.setattr(setups, "QComboBox", _FakeCombo)
    connect_rows: list[int] = []

    def fake_connect(_table: QTableWidget, _combo: _FakeCombo, row: int) -> None:
        connect_rows.append(row)

    monkeypatch.setattr(setups, "connect_combo_resize_on_first_row", fake_connect)

    table = cast(QTableWidget, _FakeTable(row_count=1))
    old_combo = _FakeCombo({10: 2})
    old_combo.setCurrentIndex(2)
    fake = cast(_FakeTable, table)
    fake.setCellWidget(0, 2, old_combo)

    setups.refresh_abx_reference_rows(
        table=table,
        create_abx_combo=cast(setups.CreateComboFn, lambda: _FakeCombo({10: 5})),
    )

    new_combo = cast(_FakeCombo, fake.cellWidget(0, 2))
    assert new_combo.current_index == 5
    assert connect_rows == [0]


def test_refresh_ismp_reference_rows_preserves_selected_value(monkeypatch) -> None:
    monkeypatch.setattr(setups, "QComboBox", _FakeCombo)
    connect_rows: list[int] = []

    def fake_connect(_table: QTableWidget, _combo: _FakeCombo, row: int) -> None:
        connect_rows.append(row)

    monkeypatch.setattr(setups, "connect_combo_resize_on_first_row", fake_connect)

    table = cast(QTableWidget, _FakeTable(row_count=1))
    old_combo = _FakeCombo({"VAP": 3})
    old_combo.setCurrentIndex(3)
    fake = cast(_FakeTable, table)
    fake.setCellWidget(0, 0, old_combo)

    setups.refresh_ismp_reference_rows(
        table=table,
        create_type_combo=cast(setups.CreateComboFn, lambda: _FakeCombo({"VAP": 1})),
    )

    new_combo = cast(_FakeCombo, fake.cellWidget(0, 0))
    assert new_combo.current_index == 1
    assert connect_rows == [0]
