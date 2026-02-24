from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, cast

from PySide6.QtWidgets import QTableWidget

import app.ui.emz.form_table_collectors as collectors


class _FakeItem:
    def __init__(self, value: str) -> None:
        self._value = value

    def text(self) -> str:
        return self._value


class _FakeCombo:
    def __init__(self, text: str = "", data: object | None = None) -> None:
        self._text = text
        self._data = data

    def currentText(self) -> str:  # noqa: N802
        return self._text

    def currentData(self) -> object | None:  # noqa: N802
        return self._data


class _FakeQDate:
    def __init__(self, value: date) -> None:
        self._value = value

    def toPython(self) -> date:  # noqa: N802
        return self._value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _FakeQDate):
            return self._value == other._value
        return False


class _FakeDateEdit:
    def __init__(self, qdate: _FakeQDate) -> None:
        self._qdate = qdate

    def date(self) -> _FakeQDate:
        return self._qdate


class _FakeTable:
    def __init__(self, row_count: int = 0) -> None:
        self._row_count = row_count
        self.widgets: dict[tuple[int, int], object] = {}
        self.items: dict[tuple[int, int], _FakeItem] = {}

    def rowCount(self) -> int:  # noqa: N802
        return self._row_count

    def cellWidget(self, row: int, col: int) -> object | None:  # noqa: N802
        return self.widgets.get((row, col))

    def item(self, row: int, col: int) -> _FakeItem | None:
        return self.items.get((row, col))


def test_collect_diagnoses_maps_row_with_kind_and_text(monkeypatch) -> None:
    monkeypatch.setattr(collectors, "QComboBox", _FakeCombo)
    table = _FakeTable(row_count=1)
    table.widgets[(0, 0)] = _FakeCombo(text="Поступление")
    table.widgets[(0, 1)] = _FakeCombo(data="A00")
    table.items[(0, 2)] = _FakeItem("diag")

    result = collectors.collect_diagnoses(table=cast(QTableWidget, table))
    assert len(result) == 1
    assert result[0].kind == "admission"
    assert result[0].icd10_code == "A00"
    assert result[0].free_text == "diag"


def test_collect_interventions_maps_duration_and_notes(monkeypatch) -> None:
    monkeypatch.setattr(collectors, "QComboBox", _FakeCombo)
    table = _FakeTable(row_count=1)
    table.widgets[(0, 0)] = _FakeCombo(text="ИВЛ")
    table.items[(0, 3)] = _FakeItem("30")
    table.items[(0, 4)] = _FakeItem("doc")
    table.items[(0, 5)] = _FakeItem("note")
    dt_map: dict[tuple[int, int], datetime] = {
        (0, 1): datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        (0, 2): datetime(2026, 2, 1, 11, 0, tzinfo=UTC),
    }

    result = collectors.collect_interventions(
        table=cast(QTableWidget, table),
        dt_resolver=lambda _table, row, col: dt_map.get((row, col)),
    )
    assert len(result) == 1
    assert result[0].type == "ИВЛ"
    assert result[0].duration_minutes == 30
    assert result[0].performed_by == "doc"
    assert result[0].notes == "note"


def test_collect_abx_maps_from_combo_and_free_text(monkeypatch) -> None:
    monkeypatch.setattr(collectors, "QComboBox", _FakeCombo)
    table = _FakeTable(row_count=1)
    table.widgets[(0, 2)] = _FakeCombo(data=7)
    table.items[(0, 3)] = _FakeItem("Амоксициллин")
    table.items[(0, 4)] = _FakeItem("в/в")
    dt_map: dict[tuple[int, int], datetime] = {
        (0, 0): datetime(2026, 2, 1, 8, 0, tzinfo=UTC),
        (0, 1): datetime(2026, 2, 1, 9, 0, tzinfo=UTC),
    }

    result = collectors.collect_abx(
        table=cast(QTableWidget, table),
        dt_resolver=lambda _table, row, col: dt_map.get((row, col)),
    )
    assert len(result) == 1
    assert result[0].antibiotic_id == 7
    assert result[0].drug_name_free == "Амоксициллин"
    assert result[0].route == "в/в"


def test_collect_ismp_skips_empty_and_maps_valid_row(monkeypatch) -> None:
    monkeypatch.setattr(collectors, "QComboBox", _FakeCombo)
    monkeypatch.setattr(collectors, "QDateEdit", _FakeDateEdit)
    table = _FakeTable(row_count=2)
    empty_qdate = _FakeQDate(date(2024, 1, 1))
    valid_qdate = _FakeQDate(date(2026, 2, 1))
    table.widgets[(0, 0)] = _FakeCombo(data="VAP")
    table.widgets[(0, 1)] = _FakeDateEdit(empty_qdate)
    table.widgets[(1, 0)] = _FakeCombo(data="VAP")
    table.widgets[(1, 1)] = _FakeDateEdit(valid_qdate)

    result = collectors.collect_ismp(
        table=cast(QTableWidget, table),
        date_empty=cast(Any, empty_qdate),
    )
    assert len(result) == 1
    assert result[0].ismp_type == "VAP"
    assert result[0].start_date == date(2026, 2, 1)
