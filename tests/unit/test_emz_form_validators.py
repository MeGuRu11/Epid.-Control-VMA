from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from PySide6.QtWidgets import QTableWidget

from app.ui.emz.form_validators import (
    validate_datetime_cell,
    validate_datetime_range,
    validate_required_fields,
    validate_table_datetime_rows,
)


class _FakeItem:
    def __init__(self, value: str) -> None:
        self._value = value

    def text(self) -> str:
        return self._value


class _FakeTable:
    def __init__(self, items: dict[tuple[int, int], str], headers: dict[int, str], row_count: int = 1) -> None:
        self._items = items
        self._headers = headers
        self._row_count = row_count

    def item(self, row: int, col: int) -> _FakeItem | None:
        value = self._items.get((row, col))
        if value is None:
            return None
        return _FakeItem(value)

    def horizontalHeaderItem(self, col: int) -> _FakeItem | None:  # noqa: N802
        value = self._headers.get(col)
        if value is None:
            return None
        return _FakeItem(value)

    def rowCount(self) -> int:  # noqa: N802
        return self._row_count


def test_validate_required_fields_messages() -> None:
    assert (
        validate_required_fields(full_name="", hospital_case_no="123", category_value="x")
        == "Укажите ФИО и № истории болезни"
    )
    assert (
        validate_required_fields(full_name="Иван", hospital_case_no="123", category_value=None)
        == "Укажите категорию военнослужащего"
    )
    assert validate_required_fields(full_name="Иван", hospital_case_no="123", category_value="x") is None


def test_validate_datetime_cell_returns_error_message() -> None:
    table = cast(QTableWidget, _FakeTable(items={(0, 1): "bad-dt"}, headers={1: "Дата"}))
    error = validate_datetime_cell(
        table=table,
        row=0,
        col=1,
        dt_resolver=lambda _table, _row, _col: None,
    )
    assert error == "Неверный формат даты/времени в строке 1 (Дата): bad-dt"


def test_validate_datetime_cell_returns_none_for_empty_text() -> None:
    table = cast(QTableWidget, _FakeTable(items={(0, 1): "   "}, headers={1: "Дата"}))
    error = validate_datetime_cell(
        table=table,
        row=0,
        col=1,
        dt_resolver=lambda _table, _row, _col: None,
    )
    assert error is None


def test_validate_datetime_range_returns_error() -> None:
    table = cast(QTableWidget, _FakeTable(items={}, headers={}))
    values: dict[tuple[int, int], datetime] = {
        (0, 1): datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
        (0, 2): datetime(2025, 1, 1, 10, 0, tzinfo=UTC),
    }
    error = validate_datetime_range(
        table=table,
        row=0,
        start_col=1,
        end_col=2,
        dt_resolver=lambda _table, row, col: values.get((row, col)),
    )
    assert error == "Дата начала не может быть позже окончания"


def test_validate_datetime_range_returns_none_when_order_ok() -> None:
    table = cast(QTableWidget, _FakeTable(items={}, headers={}))
    values: dict[tuple[int, int], datetime] = {
        (0, 1): datetime(2025, 1, 1, 10, 0, tzinfo=UTC),
        (0, 2): datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
    }
    error = validate_datetime_range(
        table=table,
        row=0,
        start_col=1,
        end_col=2,
        dt_resolver=lambda _table, row, col: values.get((row, col)),
    )
    assert error is None


def test_validate_table_datetime_rows_returns_first_error() -> None:
    table = cast(QTableWidget, _FakeTable(items={(0, 1): "bad"}, headers={1: "Дата"}))
    error = validate_table_datetime_rows(
        table=table,
        datetime_cols=(1,),
        range_pairs=(),
        dt_resolver=lambda _table, _row, _col: None,
    )
    assert error == "Неверный формат даты/времени в строке 1 (Дата): bad"
