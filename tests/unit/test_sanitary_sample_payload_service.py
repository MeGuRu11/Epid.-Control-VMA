from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.application.services.sanitary_sample_payload_service import (
    PhageInput,
    SusceptibilityInput,
    build_phage_payload,
    build_sanitary_result_update,
    build_sanitary_sample_create_request,
    build_sanitary_sample_update_request,
    build_susceptibility_payload,
    has_sanitary_result_data,
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


def test_has_sanitary_result_data_detects_main_fields() -> None:
    assert (
        has_sanitary_result_data(
            growth_flag=1,
            colony_desc="",
            microscopy="",
            cfu="",
            microorganism_id=None,
            microorganism_free="",
            susceptibility_rows=[],
            phage_rows=[],
        )
        is True
    )
    assert (
        has_sanitary_result_data(
            growth_flag=None,
            colony_desc="growth",
            microscopy="",
            cfu="",
            microorganism_id=None,
            microorganism_free="",
            susceptibility_rows=[],
            phage_rows=[],
        )
        is True
    )


def test_has_sanitary_result_data_detects_table_values() -> None:
    assert (
        has_sanitary_result_data(
            growth_flag=None,
            colony_desc="",
            microscopy="",
            cfu="",
            microorganism_id=None,
            microorganism_free="",
            susceptibility_rows=[SusceptibilityInput(1, 2, None, None, None)],
            phage_rows=[],
        )
        is True
    )
    assert (
        has_sanitary_result_data(
            growth_flag=None,
            colony_desc="",
            microscopy="",
            cfu="",
            microorganism_id=None,
            microorganism_free="",
            susceptibility_rows=[],
            phage_rows=[PhageInput(1, None, "custom", None)],
        )
        is True
    )


def test_has_sanitary_result_data_returns_false_when_all_empty() -> None:
    assert (
        has_sanitary_result_data(
            growth_flag=None,
            colony_desc=" ",
            microscopy="",
            cfu="",
            microorganism_id=None,
            microorganism_free=" ",
            susceptibility_rows=[],
            phage_rows=[],
        )
        is False
    )


def test_build_sanitary_sample_create_request_normalizes_optional_fields() -> None:
    request = build_sanitary_sample_create_request(
        department_id=1,
        sampling_point="  Door handle  ",
        room="  ",
        medium=" Blood agar ",
        taken_at=None,
        delivered_at=None,
        created_by=7,
    )
    assert request.department_id == 1
    assert request.sampling_point == "Door handle"
    assert request.room is None
    assert request.medium == "Blood agar"
    assert request.created_by == 7


def test_build_sanitary_sample_create_request_requires_sampling_point() -> None:
    with pytest.raises(ValueError, match="Укажите точку отбора"):
        build_sanitary_sample_create_request(
            department_id=1,
            sampling_point="  ",
            room="",
            medium="",
            taken_at=None,
            delivered_at=None,
        )


def test_build_sanitary_sample_update_request_requires_sampling_point() -> None:
    with pytest.raises(ValueError, match="Укажите точку отбора"):
        build_sanitary_sample_update_request(
            sampling_point=" ",
            room="",
            medium="",
            taken_at=None,
            delivered_at=None,
        )


def test_build_sanitary_result_update_sets_timestamp_for_filled_results() -> None:
    update = build_sanitary_result_update(
        has_results=True,
        growth_flag=1,
        growth_result_at=None,
        colony_desc="",
        microscopy="micro",
        cfu="10^5",
        microorganism_id=10,
        microorganism_free="",
        susceptibility=[{"antibiotic_id": 1}],
        phages=[{"phage_id": 2}],
    )
    assert update.growth_flag == 1
    assert update.growth_result_at is not None
    assert isinstance(update.growth_result_at, datetime)
    assert update.colony_desc is None
    assert update.microscopy == "micro"
    assert update.cfu == "10^5"
    assert update.microorganism_id == 10
    assert update.microorganism_free is None
    assert update.susceptibility == [{"antibiotic_id": 1}]
    assert update.phages == [{"phage_id": 2}]


def test_build_sanitary_result_update_clears_fields_when_no_results() -> None:
    update = build_sanitary_result_update(
        has_results=False,
        growth_flag=1,
        growth_result_at=datetime(2026, 4, 7, 12, 0, tzinfo=UTC),
        colony_desc="desc",
        microscopy="micro",
        cfu="10^5",
        microorganism_id=10,
        microorganism_free="custom",
        susceptibility=[{"antibiotic_id": 1}],
        phages=[{"phage_id": 2}],
    )
    assert update.growth_flag is None
    assert update.growth_result_at is None
    assert update.colony_desc is None
    assert update.microscopy is None
    assert update.cfu is None
    assert update.microorganism_id is None
    assert update.microorganism_free is None
    assert update.susceptibility == []
    assert update.phages == []
