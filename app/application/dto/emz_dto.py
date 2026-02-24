from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.domain.constants import IsmpType, MilitaryCategory


class EmzDiagnosisDto(BaseModel):
    kind: str = Field(..., pattern="^(admission|discharge|complication)$")
    icd10_code: str | None = None
    free_text: str | None = None


class EmzInterventionDto(BaseModel):
    type: str
    start_dt: datetime | None = None
    end_dt: datetime | None = None
    duration_minutes: int | None = None
    performed_by: str | None = None
    notes: str | None = None


class EmzAntibioticCourseDto(BaseModel):
    start_dt: datetime | None = None
    end_dt: datetime | None = None
    antibiotic_id: int | None = None
    drug_name_free: str | None = None
    route: str | None = None
    dose: str | None = None


class EmzIsmpDto(BaseModel):
    ismp_type: str
    start_date: date

    @classmethod
    @field_validator("ismp_type")
    def _validate_ismp_type(cls, v: str) -> str:
        if v not in IsmpType.values():
            raise ValueError("Неизвестный тип ИСМП")
        return v


class EmzVersionPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    admission_date: datetime | None = None
    injury_date: datetime | None = None
    outcome_date: datetime | None = None
    outcome_type: str | None = None
    severity: str | None = None
    vph_sp_score: int | None = None
    vph_p_or_score: int | None = None
    sofa_score: int | None = None

    diagnoses: list[EmzDiagnosisDto] = Field(default_factory=list)
    interventions: list[EmzInterventionDto] = Field(default_factory=list)
    antibiotic_courses: list[EmzAntibioticCourseDto] = Field(default_factory=list)
    ismp_cases: list[EmzIsmpDto] = Field(default_factory=list)

    @classmethod
    @field_validator("outcome_date")
    def _validate_dates(cls, v: datetime | None, info: ValidationInfo) -> datetime | None:
        injury = info.data.get("injury_date")
        admission = info.data.get("admission_date")
        if admission and injury and admission < injury:
            raise ValueError("Дата поступления не может быть раньше даты травмы")
        if v and admission and v < admission:
            raise ValueError("Дата исхода не может быть раньше даты поступления")
        return v


class EmzCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    patient_full_name: str
    patient_dob: date | None = None
    patient_sex: str = Field(default="U", pattern="^(M|F|U)$")
    patient_category: str = Field(..., min_length=1)
    patient_military_unit: str | None = None
    patient_military_district: str | None = None

    hospital_case_no: str
    department_id: int | None = None
    payload: EmzVersionPayload

    def to_patient_request(self):
        from app.application.dto.patient_dto import PatientCreateRequest

        return PatientCreateRequest(
            full_name=self.patient_full_name,
            dob=self.patient_dob,
            sex=self.patient_sex,
            category=self.patient_category,
            military_unit=self.patient_military_unit,
            military_district=self.patient_military_district,
        )

    @classmethod
    @field_validator("patient_category")
    def _validate_category(cls, v: str) -> str:
        if v not in MilitaryCategory.values():
            raise ValueError("Неизвестная категория военнослужащего")
        return v


class EmzUpdateRequest(BaseModel):
    emr_case_id: int
    payload: EmzVersionPayload


class EmzCaseResponse(BaseModel):
    id: int
    version_id: int
    version_no: int
    is_current: bool
    valid_from: datetime
    valid_to: datetime | None
    days_to_admission: int | None
    length_of_stay_days: int | None


class EmzCaseDetail(BaseModel):
    id: int
    patient_id: int
    patient_full_name: str
    patient_dob: date | None
    patient_sex: str
    patient_category: str | None = None
    patient_military_unit: str | None = None
    patient_military_district: str | None = None
    hospital_case_no: str
    department_id: int | None
    version_no: int
    admission_date: datetime | None
    injury_date: datetime | None
    outcome_date: datetime | None
    severity: str | None
    sofa_score: int | None
    vph_p_or_score: int | None
    diagnoses: list[EmzDiagnosisDto]
    interventions: list[EmzInterventionDto]
    antibiotic_courses: list[EmzAntibioticCourseDto]
    ismp_cases: list[EmzIsmpDto] = Field(default_factory=list)
