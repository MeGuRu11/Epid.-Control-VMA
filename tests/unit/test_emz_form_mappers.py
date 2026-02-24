from __future__ import annotations

from datetime import UTC, date, datetime

from app.ui.emz.form_mappers import (
    map_antibiotic_course,
    map_diagnosis,
    map_intervention,
    map_ismp_case,
)


def test_map_diagnosis_returns_none_for_empty_kind() -> None:
    assert map_diagnosis(raw_kind="", icd_code=None, free_text="text") is None


def test_map_diagnosis_maps_russian_kind_to_dto() -> None:
    dto = map_diagnosis(raw_kind="Поступление", icd_code="A00", free_text="")
    assert dto is not None
    assert dto.kind == "admission"
    assert dto.icd10_code == "A00"


def test_map_intervention_returns_none_for_empty_type() -> None:
    assert map_intervention("", None, None, None, None, None) is None


def test_map_intervention_parses_duration_and_trims_strings() -> None:
    dto = map_intervention(
        type_value="ИВЛ",
        start_dt=datetime(2025, 1, 1, 10, 0, tzinfo=UTC),
        end_dt=datetime(2025, 1, 1, 11, 0, tzinfo=UTC),
        duration_text="60",
        performed_by="  Dr X  ",
        notes="  note  ",
    )
    assert dto is not None
    assert dto.duration_minutes == 60
    assert dto.performed_by == "Dr X"
    assert dto.notes == "note"


def test_map_antibiotic_course_builds_dto() -> None:
    dto = map_antibiotic_course(
        start_dt=None,
        end_dt=None,
        antibiotic_id=1,
        drug_name_free="free",
        route="iv",
    )
    assert dto.antibiotic_id == 1
    assert dto.drug_name_free == "free"
    assert dto.route == "iv"


def test_map_ismp_case_requires_type_and_date() -> None:
    assert map_ismp_case(None, date(2025, 1, 1)) is None
    assert map_ismp_case("VAP", None) is None
    dto = map_ismp_case("VAP", date(2025, 1, 1))
    assert dto is not None
    assert dto.ismp_type == "VAP"
