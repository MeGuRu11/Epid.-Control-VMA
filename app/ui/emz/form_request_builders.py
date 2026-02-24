from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.application.dto.emz_dto import (
    EmzAntibioticCourseDto,
    EmzCreateRequest,
    EmzDiagnosisDto,
    EmzInterventionDto,
    EmzIsmpDto,
    EmzUpdateRequest,
    EmzVersionPayload,
)


@dataclass(frozen=True)
class PatientUpdateFields:
    full_name: str | None
    dob: date | None
    sex: str | None
    category: str | None
    military_unit: str | None
    military_district: str | None


def build_emz_version_payload(
    *,
    admission_date: datetime | None,
    injury_date: datetime | None,
    outcome_date: datetime | None,
    severity: str | None,
    sofa_score: int | None,
    vph_p_or_score: int | None,
    diagnoses: list[EmzDiagnosisDto],
    interventions: list[EmzInterventionDto],
    antibiotic_courses: list[EmzAntibioticCourseDto],
    ismp_cases: list[EmzIsmpDto],
) -> EmzVersionPayload:
    return EmzVersionPayload(
        admission_date=admission_date,
        injury_date=injury_date,
        outcome_date=outcome_date,
        severity=severity,
        sofa_score=sofa_score,
        vph_p_or_score=vph_p_or_score,
        diagnoses=diagnoses,
        interventions=interventions,
        antibiotic_courses=antibiotic_courses,
        ismp_cases=ismp_cases,
    )


def build_emz_create_request(
    *,
    patient_full_name: str,
    patient_dob: date | None,
    patient_sex: str,
    patient_category: str,
    patient_military_unit: str | None,
    patient_military_district: str | None,
    hospital_case_no: str,
    department_id: int | None,
    payload: EmzVersionPayload,
) -> EmzCreateRequest:
    return EmzCreateRequest(
        patient_full_name=patient_full_name,
        patient_dob=patient_dob,
        patient_sex=patient_sex,
        patient_category=patient_category,
        patient_military_unit=patient_military_unit,
        patient_military_district=patient_military_district,
        hospital_case_no=hospital_case_no,
        department_id=department_id,
        payload=payload,
    )


def build_emz_update_request(
    *,
    emr_case_id: int,
    payload: EmzVersionPayload,
) -> EmzUpdateRequest:
    return EmzUpdateRequest(emr_case_id=emr_case_id, payload=payload)


def build_patient_update_fields(
    *,
    full_name: str | None,
    dob: date | None,
    sex: str | None,
    category: str | None,
    military_unit: str | None,
    military_district: str | None,
) -> PatientUpdateFields:
    return PatientUpdateFields(
        full_name=full_name,
        dob=dob,
        sex=sex,
        category=category,
        military_unit=military_unit,
        military_district=military_district,
    )
