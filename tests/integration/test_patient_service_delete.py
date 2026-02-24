from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.patient_dto import PatientCreateRequest
from app.application.services.patient_service import PatientService
from app.domain.constants import MilitaryCategory
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.fts_manager import FtsManager
from app.infrastructure.db.models_sqlalchemy import Base
from app.infrastructure.db.repositories.patient_repo import PatientRepository


def make_session_factory(db_path: Path) -> Callable[[], AbstractContextManager[Session]]:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
    )

    @contextmanager
    def _session_scope() -> Iterator[Session]:
        session: Session = session_local()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return _session_scope


def _seed_related_entities(session: Session, patient_id: int) -> tuple[int, int]:
    material_type = models.RefMaterialType(code="MAT-1", name="Material")
    abx_group = models.RefAntibioticGroup(code="GRP-1", name="Group")
    antibiotic = models.RefAntibiotic(code="ABX-1", name="Antibiotic", group=abx_group)
    session.add_all([material_type, abx_group, antibiotic])
    session.flush()

    emr_case = models.EmrCase(patient_id=patient_id, hospital_case_no="CASE-1")
    session.add(emr_case)
    session.flush()

    emr_case_version = models.EmrCaseVersion(
        emr_case_id=emr_case.id,
        version_no=1,
        valid_from=datetime(2026, 2, 12, 8, 0, tzinfo=UTC),
        valid_to=None,
        is_current=True,
    )
    session.add(emr_case_version)
    session.flush()

    session.add_all(
        [
            models.EmrDiagnosis(emr_case_version_id=emr_case_version.id, kind="admission"),
            models.EmrIntervention(emr_case_version_id=emr_case_version.id, type="intv"),
            models.EmrAntibioticCourse(emr_case_version_id=emr_case_version.id, antibiotic_id=antibiotic.id),
        ]
    )

    lab_sample = models.LabSample(
        patient_id=patient_id,
        emr_case_id=emr_case.id,
        lab_no="LAB-1",
        material_type_id=material_type.id,
    )
    session.add(lab_sample)
    session.flush()

    session.add_all(
        [
            models.LabMicrobeIsolation(lab_sample_id=lab_sample.id, microorganism_free="micro"),
            models.LabAbxSusceptibility(lab_sample_id=lab_sample.id, antibiotic_id=antibiotic.id),
            models.LabPhagePanelResult(lab_sample_id=lab_sample.id, phage_free="phage"),
        ]
    )
    session.flush()

    session.add_all(
        [
            models.AuditLog(entity_type="patient", entity_id=str(patient_id), action="update"),
            models.AuditLog(entity_type="emr_case", entity_id=str(emr_case.id), action="update"),
            models.AuditLog(entity_type="lab_sample", entity_id=str(lab_sample.id), action="update"),
            models.AuditLog(entity_type="other", entity_id="keep", action="keep"),
        ]
    )
    return cast(int, emr_case.id), cast(int, lab_sample.id)


def test_delete_patient_removes_related_rows_and_keeps_unrelated_audit(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "patient_delete.db")
    service = PatientService(
        patient_repo=PatientRepository(),
        session_factory=session_factory,
        fts_manager=FtsManager(session_factory=session_factory),
    )

    created = service.create_or_get(
        PatientCreateRequest(
            full_name="Ivan Ivanov",
            dob=date(2000, 1, 1),
            sex="M",
            category=MilitaryCategory.CIVILIAN_STAFF.value,
            military_unit="unit",
            military_district="district",
        )
    )

    with session_factory() as session:
        _seed_related_entities(session, created.id)

    service.delete_patient(created.id)

    with session_factory() as session:
        assert session.query(models.Patient).count() == 0
        assert session.query(models.EmrCase).count() == 0
        assert session.query(models.EmrCaseVersion).count() == 0
        assert session.query(models.EmrDiagnosis).count() == 0
        assert session.query(models.EmrIntervention).count() == 0
        assert session.query(models.EmrAntibioticCourse).count() == 0
        assert session.query(models.LabSample).count() == 0
        assert session.query(models.LabMicrobeIsolation).count() == 0
        assert session.query(models.LabAbxSusceptibility).count() == 0
        assert session.query(models.LabPhagePanelResult).count() == 0

        audit_rows = session.query(models.AuditLog).all()
        assert len(audit_rows) == 1
        assert audit_rows[0].entity_type == "other"
        assert audit_rows[0].entity_id == "keep"


def test_delete_patient_raises_for_missing_patient(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "patient_delete_missing.db")
    service = PatientService(
        patient_repo=PatientRepository(),
        session_factory=session_factory,
        fts_manager=FtsManager(session_factory=session_factory),
    )

    with pytest.raises(ValueError):
        service.delete_patient(99999)
