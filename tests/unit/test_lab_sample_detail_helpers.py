from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest
from PySide6.QtCore import QDate, QDateTime, QTime
from PySide6.QtWidgets import QDateTimeEdit

from app.ui.lab.lab_sample_detail import LabSampleDetailDialog
from app.ui.lab.lab_sample_detail_helpers import (
    PhageInput,
    SusceptibilityInput,
    build_phage_payload,
    build_susceptibility_payload,
    compose_lab_result_update,
    has_lab_result_data,
)
from app.ui.widgets.datetime_inputs import DEFAULT_EMPTY_DATETIME


def test_build_susceptibility_payload_normalizes_and_parses() -> None:
    payload = build_susceptibility_payload(
        [
            SusceptibilityInput(
                row_number=1,
                antibiotic_id=10,
                ris=" s ",
                mic_text="0.5",
                method="disk",
            )
        ]
    )
    assert payload == [{"antibiotic_id": 10, "ris": "S", "mic_mg_l": 0.5, "method": "disk"}]


def test_build_susceptibility_payload_requires_antibiotic_for_filled_row() -> None:
    with pytest.raises(ValueError, match="Выберите антибиотик в строке 2"):
        build_susceptibility_payload(
            [SusceptibilityInput(row_number=2, antibiotic_id=None, ris="R", mic_text=None, method=None)]
        )


def test_build_susceptibility_payload_rejects_invalid_ris() -> None:
    with pytest.raises(ValueError, match="RIS должен быть R/I/S"):
        build_susceptibility_payload(
            [SusceptibilityInput(row_number=1, antibiotic_id=1, ris="X", mic_text=None, method=None)]
        )


def test_build_phage_payload_requires_choice_or_free_name() -> None:
    with pytest.raises(ValueError, match="Укажите фаг или свободное имя в строке 3"):
        build_phage_payload([PhageInput(row_number=3, phage_id=None, phage_free=" ", diameter_text="5")])


def test_build_phage_payload_rejects_negative_diameter() -> None:
    with pytest.raises(ValueError, match="Диаметр должен быть >= 0"):
        build_phage_payload([PhageInput(row_number=1, phage_id=7, phage_free="", diameter_text="-1")])


def test_has_lab_result_data_detects_header_and_table_values() -> None:
    assert (
        has_lab_result_data(
            growth_flag=None,
            colony_desc="",
            microscopy="",
            cfu="",
            microorganism_id=None,
            microorganism_free="",
            susceptibility_rows=[SusceptibilityInput(1, 5, None, None, None)],
            phage_rows=[],
        )
        is True
    )
    assert (
        has_lab_result_data(
            growth_flag=None,
            colony_desc="",
            microscopy="",
            cfu="",
            microorganism_id=None,
            microorganism_free="",
            susceptibility_rows=[],
            phage_rows=[],
        )
        is False
    )


def test_compose_lab_result_update_clears_result_fields_when_no_results() -> None:
    update = compose_lab_result_update(
        has_results=False,
        growth_flag=1,
        growth_result_at=datetime(2026, 2, 13, 12, 0, tzinfo=UTC),
        colony_desc="desc",
        microscopy="micro",
        cfu="1e5",
        qc_status="valid",
        microorganism_id=100,
        microorganism_free="free",
        susceptibility=[{"antibiotic_id": 1}],
        phages=[{"phage_id": 2}],
    )
    assert update.growth_flag is None
    assert update.growth_result_at is None
    assert update.colony_desc is None
    assert update.microscopy is None
    assert update.cfu is None
    assert update.qc_status == "valid"
    assert update.microorganism_id is None
    assert update.microorganism_free is None
    assert update.susceptibility == []
    assert update.phages == []


class _LabServiceStub:
    pass


class _LabReferenceServiceStub:
    def list_material_types(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="BLD", name="Blood")]

    def list_microorganisms(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="STA", name="Staphylococcus aureus")]

    def search_microorganisms(self, _query: str, *, limit: int) -> list[SimpleNamespace]:
        return self.list_microorganisms()[:limit]

    def list_antibiotics(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="AMK", name="Amikacin")]

    def list_phages(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="PH", name="Phage")]


def test_lab_detail_datetime_fields_start_empty_and_keep_explicit_time(qapp) -> None:
    dialog = LabSampleDetailDialog(
        lab_service=cast(Any, _LabServiceStub()),
        reference_service=cast(Any, _LabReferenceServiceStub()),
        patient_id=1,
        emr_case_id=None,
        actor_id=7,
    )
    try:
        dialog.show()
        qapp.processEvents()

        widgets = [dialog.ordered_at, dialog.taken_at, dialog.delivered_at, dialog.growth_result_at]
        for widget in widgets:
            assert isinstance(widget, QDateTimeEdit)
            assert widget.displayFormat() == "dd.MM.yyyy HH:mm"
            assert widget.dateTime() == DEFAULT_EMPTY_DATETIME
            assert dialog._to_python_datetime(widget) is None

        dialog.taken_at.setDateTime(QDateTime(QDate(2024, 1, 1), QTime(8, 30)))
        value = dialog._to_python_datetime(dialog.taken_at)

        assert value is not None
        assert value.hour == 8
        assert value.minute == 30
    finally:
        dialog.close()
