from __future__ import annotations

from datetime import UTC, date, datetime

from app.application.dto.emz_dto import EmzVersionPayload
from app.ui.emz.form_request_builders import (
    build_emz_create_request,
    build_emz_update_request,
    build_emz_version_payload,
    build_patient_update_fields,
)


def _build_payload() -> EmzVersionPayload:
    return EmzVersionPayload(
        admission_date=datetime(2026, 2, 10, 10, 0, tzinfo=UTC),
        injury_date=datetime(2026, 2, 9, 9, 0, tzinfo=UTC),
        diagnoses=[],
        interventions=[],
        antibiotic_courses=[],
        ismp_cases=[],
    )


def test_build_emz_create_request_maps_all_fields() -> None:
    payload = _build_payload()
    request = build_emz_create_request(
        patient_full_name="Ivanov Ivan",
        patient_dob=date(1990, 1, 1),
        patient_sex="M",
        patient_category="CONSCRIPT",
        patient_military_unit="123",
        patient_military_district="ZVO",
        hospital_case_no="HC-1",
        department_id=10,
        payload=payload,
    )
    assert request.patient_full_name == "Ivanov Ivan"
    assert request.patient_dob == date(1990, 1, 1)
    assert request.patient_sex == "M"
    assert request.patient_category == "CONSCRIPT"
    assert request.patient_military_unit == "123"
    assert request.patient_military_district == "ZVO"
    assert request.hospital_case_no == "HC-1"
    assert request.department_id == 10
    assert request.payload == payload


def test_build_emz_update_request_maps_fields() -> None:
    payload = _build_payload()
    request = build_emz_update_request(emr_case_id=5, payload=payload)
    assert request.emr_case_id == 5
    assert request.payload == payload


def test_build_patient_update_fields_maps_fields() -> None:
    fields = build_patient_update_fields(
        full_name="Petrov Petr",
        dob=date(1991, 5, 5),
        sex="F",
        category="OFFICER",
        military_unit="321",
        military_district="YUVO",
    )
    assert fields.full_name == "Petrov Petr"
    assert fields.dob == date(1991, 5, 5)
    assert fields.sex == "F"
    assert fields.category == "OFFICER"
    assert fields.military_unit == "321"
    assert fields.military_district == "YUVO"


def test_build_emz_version_payload_maps_all_fields() -> None:
    admission_date = datetime(2026, 2, 15, 8, 0, tzinfo=UTC)
    injury_date = datetime(2026, 2, 14, 23, 30, tzinfo=UTC)
    outcome_date = datetime(2026, 2, 20, 11, 45, tzinfo=UTC)
    payload = build_emz_version_payload(
        admission_date=admission_date,
        injury_date=injury_date,
        outcome_date=outcome_date,
        severity="medium",
        sofa_score=3,
        vph_p_or_score=5,
        diagnoses=[],
        interventions=[],
        antibiotic_courses=[],
        ismp_cases=[],
    )
    assert payload.admission_date == admission_date
    assert payload.injury_date == injury_date
    assert payload.outcome_date == outcome_date
    assert payload.severity == "medium"
    assert payload.sofa_score == 3
    assert payload.vph_p_or_score == 5
