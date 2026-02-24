from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.services.analytics_service import AnalyticsService
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.models_sqlalchemy import Base


def make_session_factory(db_path: Path) -> Callable[[], AbstractContextManager[Session]]:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
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


def _seed_analytics_dataset(
    session_factory: Callable[[], AbstractContextManager[Session]],
) -> dict[str, int | str]:
    with session_factory() as session:
        dep = models.Department(name="ICU")
        session.add(dep)
        session.flush()

        material = models.RefMaterialType(code="BLOOD", name="Blood")
        session.add(material)
        session.flush()

        icd = models.RefICD10(code="A00", title="Cholera")
        session.add(icd)
        session.flush()

        micro1 = models.RefMicroorganism(code="ECO", name="E. coli")
        micro2 = models.RefMicroorganism(code="SAU", name="S. aureus")
        session.add_all([micro1, micro2])
        session.flush()

        abx1 = models.RefAntibiotic(code="AMX", name="Amoxicillin")
        abx2 = models.RefAntibiotic(code="CIP", name="Ciprofloxacin")
        session.add_all([abx1, abx2])
        session.flush()

        patient = models.Patient(
            full_name="Иванов Иван",
            dob=datetime(1990, 1, 1, tzinfo=UTC).date(),
            category="service",
        )
        session.add(patient)
        session.flush()

        emr_case = models.EmrCase(
            patient_id=patient.id,
            hospital_case_no="CASE-001",
            department_id=dep.id,
        )
        session.add(emr_case)
        session.flush()

        case_version = models.EmrCaseVersion(
            emr_case_id=emr_case.id,
            version_no=1,
            valid_from=datetime.now(UTC),
            is_current=True,
            admission_date=datetime.now(UTC),
            length_of_stay_days=10,
        )
        session.add(case_version)
        session.flush()

        diagnosis = models.EmrDiagnosis(
            emr_case_version_id=case_version.id,
            kind="admission",
            icd10_code=icd.code,
        )
        session.add(diagnosis)
        session.flush()

        sample = models.LabSample(
            patient_id=patient.id,
            emr_case_id=emr_case.id,
            lab_no="LAB-0001",
            material_type_id=material.id,
            taken_at=datetime.now(UTC),
            growth_flag=1,
        )
        session.add(sample)
        session.flush()

        session.add_all(
            [
                models.LabMicrobeIsolation(lab_sample_id=sample.id, microorganism_id=micro1.id),
                models.LabMicrobeIsolation(lab_sample_id=sample.id, microorganism_id=micro2.id),
            ]
        )
        session.add_all(
            [
                models.LabAbxSusceptibility(lab_sample_id=sample.id, antibiotic_id=abx1.id, ris="S"),
                models.LabAbxSusceptibility(lab_sample_id=sample.id, antibiotic_id=abx2.id, ris="R"),
            ]
        )
        session.flush()

        return {
            "department_id": int(dep.id),
            "material_type_id": int(material.id),
            "microorganism_id": int(micro1.id),
            "antibiotic_id": int(abx2.id),
            "icd10_code": str(icd.code),
        }


def test_search_samples_returns_unique_sample_row(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "analytics_queries.db")
    _seed_analytics_dataset(session_factory)
    service = AnalyticsService(session_factory=session_factory)

    rows = service.search_samples(AnalyticsSearchRequest())

    assert len(rows) == 1
    assert rows[0].lab_no == "LAB-0001"
    assert rows[0].microorganism in {"ECO - E. coli", "SAU - S. aureus"}
    assert rows[0].antibiotic in {"AMX - Amoxicillin", "CIP - Ciprofloxacin"}


def test_get_aggregates_counts_microbes_without_cross_product(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "analytics_aggregates.db")
    _seed_analytics_dataset(session_factory)
    service = AnalyticsService(session_factory=session_factory)

    agg = service.get_aggregates(AnalyticsSearchRequest())

    assert agg["total"] == 1
    assert agg["positives"] == 1
    top_map = dict(agg["top_microbes"])
    assert top_map.get("ECO - E. coli") == 1
    assert top_map.get("SAU - S. aureus") == 1


def test_search_and_aggregate_filter_chain_uses_exists(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "analytics_filters.db")
    ids = _seed_analytics_dataset(session_factory)
    service = AnalyticsService(session_factory=session_factory)

    req = AnalyticsSearchRequest(
        department_id=int(ids["department_id"]),
        material_type_id=int(ids["material_type_id"]),
        microorganism_id=int(ids["microorganism_id"]),
        antibiotic_id=int(ids["antibiotic_id"]),
        icd10_code=str(ids["icd10_code"]),
        growth_flag=1,
        patient_category="service",
        lab_no="LAB-0001",
    )
    rows = service.search_samples(req)
    agg = service.get_aggregates(req)

    assert len(rows) == 1
    assert agg["total"] == 1
    assert agg["positives"] == 1
