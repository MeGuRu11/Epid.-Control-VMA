from __future__ import annotations

from datetime import date

from app.application.services.auth_service import AuthService
from app.application.services.emr_service import EmrService
from app.application.services.lab_service import LabService
from app.application.services.patient_service import PatientService
from app.application.services.reference_service import ReferenceService


def _bootstrap(engine):
    auth = AuthService(engine)
    auth.create_initial_admin("admin", "admin1234")
    session = auth.login("admin", "admin1234")
    assert session is not None
    return session


def test_emr_versioning(engine):
    session = _bootstrap(engine)
    refs = ReferenceService(engine, session)
    refs.departments()

    patients = PatientService(engine, session)
    emr = EmrService(engine, session)

    patient_id = patients.create("Тестовый Пациент", "M", None)
    case_id = emr.ensure_case(patient_id, "IB-001", "Хирургия")

    v1 = emr.create_new_version(
        case_id,
        {
            "admission_date": date(2026, 2, 1),
            "injury_date": date(2026, 1, 30),
            "outcome_date": date(2026, 2, 10),
            "severity": "средняя",
            "sofa_score": 4,
        },
    )
    v2 = emr.create_new_version(
        case_id,
        {
            "admission_date": date(2026, 2, 1),
            "injury_date": date(2026, 1, 30),
            "outcome_date": date(2026, 2, 12),
            "severity": "тяжелая",
            "sofa_score": 8,
        },
    )
    assert v2 > v1

    versions = emr.versions(case_id)
    assert len(versions) == 2
    assert versions[0].is_current is True
    assert versions[0].version_no == 2
    assert versions[1].is_current is False


def test_lab_auto_number_and_filter(engine):
    session = _bootstrap(engine)
    patients = PatientService(engine, session)
    labs = LabService(engine, session)

    patient_id = patients.create("Лаб Пациент", "M", None)
    id1 = labs.create_auto(patient_id=patient_id, material="Кровь", organism="S. aureus")
    id2 = labs.create_auto(patient_id=patient_id, material="Кровь", organism="")
    assert id2 > id1

    rows = labs.list(patient_id=patient_id)
    assert len(rows) == 2
    assert rows[0].patient_id == patient_id

