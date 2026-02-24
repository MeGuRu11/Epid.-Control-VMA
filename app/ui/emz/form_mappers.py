from __future__ import annotations

from datetime import date, datetime

from app.application.dto.emz_dto import (
    EmzAntibioticCourseDto,
    EmzDiagnosisDto,
    EmzInterventionDto,
    EmzIsmpDto,
)
from app.ui.emz.form_utils import diagnosis_kind_to_dto


def map_diagnosis(
    raw_kind: str,
    icd_code: str | None,
    free_text: str | None,
) -> EmzDiagnosisDto | None:
    kind = raw_kind.strip().lower()
    has_text = bool(free_text and free_text.strip())
    if not kind or not (icd_code or has_text):
        return None
    return EmzDiagnosisDto(
        kind=diagnosis_kind_to_dto(kind),
        icd10_code=icd_code,
        free_text=free_text,
    )


def map_intervention(
    type_value: str,
    start_dt: datetime | None,
    end_dt: datetime | None,
    duration_text: str | None,
    performed_by: str | None,
    notes: str | None,
) -> EmzInterventionDto | None:
    type_clean = type_value.strip()
    if not type_clean:
        return None
    duration_minutes = int(duration_text) if duration_text and duration_text.isdigit() else None
    return EmzInterventionDto(
        type=type_clean,
        start_dt=start_dt,
        end_dt=end_dt,
        duration_minutes=duration_minutes,
        performed_by=(performed_by or "").strip() or None,
        notes=(notes or "").strip() or None,
    )


def map_antibiotic_course(
    start_dt: datetime | None,
    end_dt: datetime | None,
    antibiotic_id: int | None,
    drug_name_free: str | None,
    route: str | None,
) -> EmzAntibioticCourseDto:
    return EmzAntibioticCourseDto(
        start_dt=start_dt,
        end_dt=end_dt,
        antibiotic_id=antibiotic_id,
        drug_name_free=drug_name_free,
        route=route,
        dose=None,
    )


def map_ismp_case(
    ismp_type: str | None,
    start_date: date | None,
) -> EmzIsmpDto | None:
    if not ismp_type or start_date is None:
        return None
    return EmzIsmpDto(ismp_type=ismp_type, start_date=start_date)
