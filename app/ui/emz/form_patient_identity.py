from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class PatientIdentityData:
    full_name: str
    dob: date | None
    sex_code: str | None
    category: str | None
    military_unit: str | None
    military_district: str | None


class PatientRecordLike(Protocol):
    @property
    def full_name(self) -> str: ...

    @property
    def dob(self) -> date | None: ...

    @property
    def sex(self) -> str | None: ...

    @property
    def category(self) -> str | None: ...

    @property
    def military_unit(self) -> str | None: ...

    @property
    def military_district(self) -> str | None: ...


class CaseDetailPatientLike(Protocol):
    @property
    def patient_full_name(self) -> str: ...

    @property
    def patient_dob(self) -> date | None: ...

    @property
    def patient_sex(self) -> str | None: ...

    @property
    def patient_category(self) -> str | None: ...

    @property
    def patient_military_unit(self) -> str | None: ...

    @property
    def patient_military_district(self) -> str | None: ...


def build_patient_identity_data(
    *,
    full_name: str,
    dob: date | None,
    sex_code: str | None,
    category: str | None,
    military_unit: str | None,
    military_district: str | None,
) -> PatientIdentityData:
    return PatientIdentityData(
        full_name=full_name,
        dob=dob,
        sex_code=sex_code,
        category=category,
        military_unit=military_unit,
        military_district=military_district,
    )


def identity_from_patient_record(record: PatientRecordLike) -> PatientIdentityData:
    return build_patient_identity_data(
        full_name=record.full_name,
        dob=record.dob,
        sex_code=record.sex,
        category=record.category,
        military_unit=record.military_unit,
        military_district=record.military_district,
    )


def identity_from_case_detail(detail: CaseDetailPatientLike) -> PatientIdentityData:
    return build_patient_identity_data(
        full_name=detail.patient_full_name,
        dob=detail.patient_dob,
        sex_code=detail.patient_sex,
        category=detail.patient_category,
        military_unit=detail.patient_military_unit,
        military_district=detail.patient_military_district,
    )
