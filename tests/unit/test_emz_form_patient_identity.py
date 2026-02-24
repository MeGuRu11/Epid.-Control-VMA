from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.ui.emz.form_patient_identity import (
    build_patient_identity_data,
    identity_from_case_detail,
    identity_from_patient_record,
)


@dataclass
class _PatientRecord:
    full_name: str
    dob: date | None
    sex: str | None
    category: str | None
    military_unit: str | None
    military_district: str | None


@dataclass
class _CaseDetail:
    patient_full_name: str
    patient_dob: date | None
    patient_sex: str | None
    patient_category: str | None
    patient_military_unit: str | None
    patient_military_district: str | None


def test_build_patient_identity_data_maps_fields() -> None:
    identity = build_patient_identity_data(
        full_name="Иванов Иван",
        dob=date(1990, 1, 1),
        sex_code="M",
        category="CONSCRIPT",
        military_unit="123",
        military_district="ЗВО",
    )
    assert identity.full_name == "Иванов Иван"
    assert identity.dob == date(1990, 1, 1)
    assert identity.sex_code == "M"
    assert identity.category == "CONSCRIPT"
    assert identity.military_unit == "123"
    assert identity.military_district == "ЗВО"


def test_identity_from_patient_record_maps_record_fields() -> None:
    record = _PatientRecord(
        full_name="Петров Петр",
        dob=date(1991, 5, 5),
        sex="F",
        category="OFFICER",
        military_unit="321",
        military_district="ЮВО",
    )
    identity = identity_from_patient_record(record)
    assert identity.full_name == "Петров Петр"
    assert identity.dob == date(1991, 5, 5)
    assert identity.sex_code == "F"
    assert identity.category == "OFFICER"
    assert identity.military_unit == "321"
    assert identity.military_district == "ЮВО"


def test_identity_from_case_detail_maps_case_fields() -> None:
    detail = _CaseDetail(
        patient_full_name="Сидоров Сидор",
        patient_dob=date(1992, 7, 7),
        patient_sex="M",
        patient_category="CONTRACT",
        patient_military_unit="555",
        patient_military_district="ЦВО",
    )
    identity = identity_from_case_detail(detail)
    assert identity.full_name == "Сидоров Сидор"
    assert identity.dob == date(1992, 7, 7)
    assert identity.sex_code == "M"
    assert identity.category == "CONTRACT"
    assert identity.military_unit == "555"
    assert identity.military_district == "ЦВО"
