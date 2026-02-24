from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, cast

from PySide6.QtWidgets import QTableWidget

import app.ui.emz.form_table_appliers as appliers
from app.application.dto.emz_dto import (
    EmzAntibioticCourseDto,
    EmzDiagnosisDto,
    EmzInterventionDto,
    EmzIsmpDto,
)


class _FakeItem:
    def __init__(self, value: str) -> None:
        self._value = value

    def text(self) -> str:
        return self._value


class _FakeCombo:
    def __init__(self, data_to_index: dict[object, int] | None = None) -> None:
        self._data_to_index = data_to_index or {}
        self.current_text = ""
        self.current_index = -1

    def setCurrentText(self, value: str) -> None:  # noqa: N802
        self.current_text = value

    def findData(self, value: object) -> int:  # noqa: N802
        return self._data_to_index.get(value, -1)

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        self.current_index = index


class _FakeDateTimeEdit:
    def __init__(self) -> None:
        self.value: Any = None

    def setDateTime(self, value: Any) -> None:  # noqa: N802
        self.value = value


class _FakeDateEdit:
    def __init__(self) -> None:
        self.value: Any = None

    def setDate(self, value: Any) -> None:  # noqa: N802
        self.value = value


class _FakeTable:
    def __init__(self, row_count: int = 0) -> None:
        self._row_count = row_count
        self.items: dict[tuple[int, int], _FakeItem] = {}
        self.widgets: dict[tuple[int, int], object] = {}

    def clearContents(self) -> None:  # noqa: N802
        self.items.clear()

    def setRowCount(self, value: int) -> None:  # noqa: N802
        self._row_count = value

    def rowCount(self) -> int:  # noqa: N802
        return self._row_count

    def cellWidget(self, row: int, col: int) -> object | None:  # noqa: N802
        return self.widgets.get((row, col))

    def setCellWidget(self, row: int, col: int, widget: object) -> None:  # noqa: N802
        self.widgets[(row, col)] = widget

    def setItem(self, row: int, col: int, item: _FakeItem) -> None:  # noqa: N802
        self.items[(row, col)] = item


def _prepare_table(table: QTableWidget, item_count: int) -> None:
    fake = cast(_FakeTable, table)
    fake.clearContents()
    fake.setRowCount(max(item_count, fake.rowCount()))


def _resize_table(_table: QTableWidget) -> None:
    return


def test_apply_diagnosis_rows_sets_kind_code_and_text(monkeypatch) -> None:
    monkeypatch.setattr(appliers, "QComboBox", _FakeCombo)
    monkeypatch.setattr(appliers, "QTableWidgetItem", _FakeItem)

    table = cast(QTableWidget, _FakeTable())

    def setup_rows() -> None:
        fake = cast(_FakeTable, table)
        for row in range(fake.rowCount()):
            fake.setCellWidget(row, 0, _FakeCombo())
            fake.setCellWidget(row, 1, _FakeCombo({"A00": 2}))

    appliers.apply_diagnosis_rows(
        table=table,
        items=[EmzDiagnosisDto(kind="admission", icd10_code="A00", free_text="test")],
        prepare_table=_prepare_table,
        setup_rows=setup_rows,
        resize_table=_resize_table,
    )

    fake = cast(_FakeTable, table)
    type_combo = cast(_FakeCombo, fake.cellWidget(0, 0))
    icd_combo = cast(_FakeCombo, fake.cellWidget(0, 1))
    assert type_combo.current_text == "Поступление"
    assert icd_combo.current_index == 2
    assert fake.items[(0, 2)].text() == "test"


def test_apply_intervention_rows_sets_widgets_and_values(monkeypatch) -> None:
    monkeypatch.setattr(appliers, "QTableWidgetItem", _FakeItem)
    resize_calls: list[int] = []
    connect_rows: list[int] = []

    def resize_table(_table: QTableWidget) -> None:
        resize_calls.append(1)

    def fake_connect(_table: QTableWidget, _combo: _FakeCombo, row: int) -> None:
        connect_rows.append(row)

    monkeypatch.setattr(appliers, "connect_combo_resize_on_first_row", fake_connect)

    table = cast(QTableWidget, _FakeTable())

    appliers.apply_intervention_rows(
        table=table,
        items=[
            EmzInterventionDto(
                type="ИВЛ",
                start_dt=datetime(2026, 1, 10, 8, 0, tzinfo=UTC),
                end_dt=datetime(2026, 1, 10, 9, 0, tzinfo=UTC),
                duration_minutes=60,
                performed_by="Иванов",
                notes="ok",
            )
        ],
        prepare_table=_prepare_table,
        resize_table=resize_table,
        create_type_combo=cast(appliers.CreateComboFn, lambda: _FakeCombo()),
        create_dt_cell=cast(appliers.CreateDateTimeEditFn, lambda: _FakeDateTimeEdit()),
        to_qdatetime=cast(appliers.ToQDateTimeFn, lambda dt: cast(Any, f"mapped:{dt.isoformat()}")),
    )

    fake = cast(_FakeTable, table)
    assert cast(_FakeCombo, fake.cellWidget(0, 0)).current_text == "ИВЛ"
    assert cast(_FakeDateTimeEdit, fake.cellWidget(0, 1)).value == "mapped:2026-01-10T08:00:00+00:00"
    assert cast(_FakeDateTimeEdit, fake.cellWidget(0, 2)).value == "mapped:2026-01-10T09:00:00+00:00"
    assert fake.items[(0, 3)].text() == "60"
    assert fake.items[(0, 4)].text() == "Иванов"
    assert fake.items[(0, 5)].text() == "ok"
    assert connect_rows == [0]
    assert len(resize_calls) == 1


def test_apply_abx_rows_sets_combo_and_text(monkeypatch) -> None:
    monkeypatch.setattr(appliers, "QComboBox", _FakeCombo)
    monkeypatch.setattr(appliers, "QTableWidgetItem", _FakeItem)

    table = cast(QTableWidget, _FakeTable())

    def setup_rows() -> None:
        fake = cast(_FakeTable, table)
        for row in range(fake.rowCount()):
            fake.setCellWidget(row, 2, _FakeCombo({7: 3}))

    appliers.apply_abx_rows(
        table=table,
        items=[
            EmzAntibioticCourseDto(
                start_dt=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
                end_dt=datetime(2026, 1, 2, 11, 0, tzinfo=UTC),
                antibiotic_id=7,
                drug_name_free="Амоксициллин",
                route="в/в",
                dose=None,
            )
        ],
        prepare_table=_prepare_table,
        setup_rows=setup_rows,
        resize_table=_resize_table,
        create_dt_cell=cast(appliers.CreateDateTimeEditFn, lambda: _FakeDateTimeEdit()),
        to_qdatetime=cast(appliers.ToQDateTimeFn, lambda dt: cast(Any, f"dt:{dt.isoformat()}")),
    )

    fake = cast(_FakeTable, table)
    abx_combo = cast(_FakeCombo, fake.cellWidget(0, 2))
    assert abx_combo.current_index == 3
    assert fake.items[(0, 3)].text() == "Амоксициллин"
    assert fake.items[(0, 4)].text() == "в/в"


def test_apply_ismp_rows_sets_combo_and_date(monkeypatch) -> None:
    connect_rows: list[int] = []

    def fake_connect(_table: QTableWidget, _combo: _FakeCombo, row: int) -> None:
        connect_rows.append(row)

    monkeypatch.setattr(appliers, "connect_combo_resize_on_first_row", fake_connect)

    table = cast(QTableWidget, _FakeTable())

    appliers.apply_ismp_rows(
        table=table,
        items=[EmzIsmpDto(ismp_type="VAP", start_date=date(2026, 2, 1))],
        prepare_table=_prepare_table,
        setup_rows=lambda: None,
        resize_table=_resize_table,
        create_type_combo=cast(appliers.CreateComboFn, lambda: _FakeCombo({"VAP": 4})),
        create_date_cell=cast(appliers.CreateDateEditFn, lambda: _FakeDateEdit()),
        to_qdate=cast(appliers.ToQDateFn, lambda d: cast(Any, f"date:{d.isoformat()}")),
    )

    fake = cast(_FakeTable, table)
    type_combo = cast(_FakeCombo, fake.cellWidget(0, 0))
    date_widget = cast(_FakeDateEdit, fake.cellWidget(0, 1))
    assert type_combo.current_index == 4
    assert date_widget.value == "date:2026-02-01"
    assert connect_rows == [0]
