from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.ui.lab.lab_sample_detail_helpers import (
    PhageInput,
    SusceptibilityInput,
    build_phage_payload,
    build_susceptibility_payload,
    compose_lab_result_update,
    has_lab_result_data,
)


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
