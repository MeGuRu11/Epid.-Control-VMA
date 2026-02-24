from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime

from PySide6.QtWidgets import QTableWidget

TableDtResolver = Callable[[QTableWidget, int, int], datetime | None]


def validate_required_fields(
    *,
    full_name: str,
    hospital_case_no: str,
    category_value: object | None,
) -> str | None:
    if not full_name.strip() or not hospital_case_no.strip():
        return "Укажите ФИО и № истории болезни"
    if category_value is None:
        return "Укажите категорию военнослужащего"
    return None


def validate_datetime_cell(
    *,
    table: QTableWidget,
    row: int,
    col: int,
    dt_resolver: TableDtResolver,
) -> str | None:
    item = table.item(row, col)
    dt_value = dt_resolver(table, row, col)
    if dt_value is not None or not item or not item.text().strip():
        return None
    header_item = table.horizontalHeaderItem(col)
    col_name = header_item.text() if header_item else f"col {col}"
    bad_value = item.text()
    return f"Неверный формат даты/времени в строке {row + 1} ({col_name}): {bad_value}"


def validate_datetime_range(
    *,
    table: QTableWidget,
    row: int,
    start_col: int,
    end_col: int,
    dt_resolver: TableDtResolver,
) -> str | None:
    start = dt_resolver(table, row, start_col)
    end = dt_resolver(table, row, end_col)
    if start and end and start > end:
        return "Дата начала не может быть позже окончания"
    return None


def validate_table_datetime_rows(
    *,
    table: QTableWidget,
    datetime_cols: Iterable[int],
    range_pairs: Iterable[tuple[int, int]],
    dt_resolver: TableDtResolver,
) -> str | None:
    for row in range(table.rowCount()):
        for col in datetime_cols:
            error = validate_datetime_cell(
                table=table,
                row=row,
                col=col,
                dt_resolver=dt_resolver,
            )
            if error:
                return error
        for start_col, end_col in range_pairs:
            error = validate_datetime_range(
                table=table,
                row=row,
                start_col=start_col,
                end_col=end_col,
                dt_resolver=dt_resolver,
            )
            if error:
                return error
    return None
