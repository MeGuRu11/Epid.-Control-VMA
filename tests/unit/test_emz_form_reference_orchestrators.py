from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from PySide6.QtWidgets import QComboBox, QDateEdit, QDateTimeEdit, QTableWidget

import app.ui.emz.form_reference_orchestrators as refs


@dataclass(frozen=True)
class _Department:
    id: int
    name: str


class _FakeCombo:
    def __init__(self) -> None:
        self.items: list[tuple[str, object]] = []
        self.current_index = -1

    def clear(self) -> None:
        self.items.clear()

    def addItem(self, label: str, data: object = None) -> None:  # noqa: N802
        self.items.append((label, data))

    def findData(self, data: object) -> int:  # noqa: N802
        for idx, (_, value) in enumerate(self.items):
            if value == data:
                return idx
        return -1

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        self.current_index = index


def test_apply_departments_to_combo_populates_and_connects() -> None:
    combo = _FakeCombo()
    connected: list[_FakeCombo] = []

    refs.apply_departments_to_combo(
        department_combo=cast(QComboBox, combo),
        departments=[_Department(id=1, name="A"), _Department(id=2, name="B")],
        connect_combo_autowidth=lambda c: connected.append(cast(_FakeCombo, c)),
    )
    assert combo.items == [("Выбрать", None), ("A", 1), ("B", 2)]
    assert connected == [combo]


def test_restore_department_selection_sets_existing_value() -> None:
    combo = _FakeCombo()
    combo.addItem("Выбрать", None)
    combo.addItem("A", 1)

    refs.restore_department_selection(
        department_combo=cast(QComboBox, combo),
        current_department=1,
    )
    assert combo.current_index == 1


def test_restore_department_selection_keeps_state_for_missing_value() -> None:
    combo = _FakeCombo()
    combo.addItem("Выбрать", None)
    combo.addItem("A", 1)

    refs.restore_department_selection(
        department_combo=cast(QComboBox, combo),
        current_department=3,
    )
    assert combo.current_index == -1


def test_setup_detail_reference_rows_calls_underlying_helpers(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        refs,
        "setup_diagnosis_rows",
        lambda **kwargs: calls.append(f"diagnosis:{kwargs['table']}"),
    )
    monkeypatch.setattr(
        refs,
        "setup_intervention_rows",
        lambda **kwargs: calls.append(f"intervention:{kwargs['table']}"),
    )
    monkeypatch.setattr(
        refs,
        "setup_abx_rows",
        lambda **kwargs: calls.append(f"abx:{kwargs['table']}"),
    )
    monkeypatch.setattr(
        refs,
        "setup_ismp_rows",
        lambda **kwargs: calls.append(f"ismp:{kwargs['table']}"),
    )

    refs.setup_detail_reference_rows(
        diagnosis_table=cast(QTableWidget, "diag"),
        intervention_table=cast(QTableWidget, "interv"),
        abx_table=cast(QTableWidget, "abx"),
        ismp_table=cast(QTableWidget, "ismp"),
        create_diag_type_combo=lambda: cast(QComboBox, "diag_type"),
        create_icd_combo=lambda: cast(QComboBox, "icd"),
        create_intervention_type_combo=lambda: cast(QComboBox, "interv_type"),
        create_dt_cell=lambda: cast(QDateTimeEdit, "dt"),
        create_abx_combo=lambda: cast(QComboBox, "abx_combo"),
        create_ismp_type_combo=lambda: cast(QComboBox, "ismp_type"),
        create_date_cell=lambda: cast(QDateEdit, "date"),
        resize_table=lambda _table: None,
    )
    assert calls == [
        "diagnosis:diag",
        "intervention:interv",
        "abx:abx",
        "ismp:ismp",
    ]


def test_refresh_detail_reference_rows_calls_helpers_and_resizes(monkeypatch) -> None:
    calls: list[str] = []
    resized: list[object] = []

    monkeypatch.setattr(
        refs,
        "refresh_diagnosis_reference_rows",
        lambda **kwargs: calls.append(f"diagnosis:{kwargs['table']}"),
    )
    monkeypatch.setattr(
        refs,
        "refresh_abx_reference_rows",
        lambda **kwargs: calls.append(f"abx:{kwargs['table']}"),
    )
    monkeypatch.setattr(
        refs,
        "refresh_ismp_reference_rows",
        lambda **kwargs: calls.append(f"ismp:{kwargs['table']}"),
    )

    refs.refresh_detail_reference_rows(
        diagnosis_table=cast(QTableWidget, "diag"),
        abx_table=cast(QTableWidget, "abx"),
        ismp_table=cast(QTableWidget, "ismp"),
        create_diag_type_combo=lambda: cast(QComboBox, "diag_type"),
        create_icd_combo=lambda: cast(QComboBox, "icd"),
        create_abx_combo=lambda: cast(QComboBox, "abx_combo"),
        create_ismp_type_combo=lambda: cast(QComboBox, "ismp_type"),
        resize_table=lambda table: resized.append(table),
    )
    assert calls == ["diagnosis:diag", "abx:abx", "ismp:ismp"]
    assert resized == ["diag", "abx", "ismp"]
