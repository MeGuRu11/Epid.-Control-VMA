from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.services.analytics_service import AnalyticsService
from app.domain.constants import IsmpType
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


def _seed_boundary_dataset(
    session_factory: Callable[[], AbstractContextManager[Session]],
) -> None:
    with session_factory() as session:
        dep = models.Department(name="ICU")
        material = models.RefMaterialType(code="BLOOD", name="Blood")
        icd = models.RefICD10(code="A00", title="Cholera")
        micro = models.RefMicroorganism(code="ECO", name="E. coli")
        abx = models.RefAntibiotic(code="AMX", name="Amoxicillin")
        session.add_all([dep, material, icd, micro, abx])
        session.flush()

        patient = models.Patient(full_name="Иванов Иван")
        session.add(patient)
        session.flush()

        emr_case = models.EmrCase(
            patient_id=patient.id,
            hospital_case_no="CASE-BOUNDARY",
            department_id=dep.id,
        )
        session.add(emr_case)
        session.flush()

        case_version = models.EmrCaseVersion(
            emr_case_id=emr_case.id,
            version_no=1,
            valid_from=datetime.now(UTC),
            is_current=True,
            admission_date=datetime(2026, 1, 31, 18, 30, tzinfo=UTC),
            length_of_stay_days=4,
        )
        session.add(case_version)
        session.flush()

        session.add(models.EmrDiagnosis(emr_case_version_id=case_version.id, kind="admission", icd10_code=icd.code))

        jan_sample = models.LabSample(
            patient_id=patient.id,
            emr_case_id=emr_case.id,
            lab_no="LAB-BOUNDARY-01",
            material_type_id=material.id,
            taken_at=datetime(2026, 1, 31, 8, 15, tzinfo=UTC),
            growth_flag=1,
        )
        feb_sample = models.LabSample(
            patient_id=patient.id,
            emr_case_id=emr_case.id,
            lab_no="LAB-BOUNDARY-02",
            material_type_id=material.id,
            taken_at=datetime(2026, 2, 1, 9, 0, tzinfo=UTC),
            growth_flag=0,
        )
        session.add_all([jan_sample, feb_sample])
        session.flush()

        session.add(models.LabMicrobeIsolation(lab_sample_id=jan_sample.id, microorganism_id=micro.id))
        session.add(models.LabAbxSusceptibility(lab_sample_id=jan_sample.id, antibiotic_id=abx.id, ris="S"))
        session.add(
            models.IsmpCase(
                emr_case_id=emr_case.id,
                ismp_type=IsmpType.VAP.value,
                start_date=date(2026, 1, 31),
            )
        )


def test_get_aggregates_includes_records_on_date_to_day(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "analytics_boundary_agg.db")
    _seed_boundary_dataset(session_factory)
    service = AnalyticsService(session_factory=session_factory)

    agg = service.get_aggregates(AnalyticsSearchRequest(date_from=date(2026, 1, 31), date_to=date(2026, 1, 31)))

    assert agg["total"] == 1
    assert agg["positives"] == 1
    assert agg["positive_share"] == 1.0


def test_get_trend_by_day_includes_end_day_rows(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "analytics_boundary_trend.db")
    _seed_boundary_dataset(session_factory)
    service = AnalyticsService(session_factory=session_factory)

    rows = service.get_trend_by_day(date(2026, 1, 31), date(2026, 1, 31))

    assert rows == [{"day": "2026-01-31", "total": 1, "positives": 1}]


def test_compare_periods_uses_inclusive_day_boundaries(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "analytics_boundary_compare.db")
    _seed_boundary_dataset(session_factory)
    service = AnalyticsService(session_factory=session_factory)

    compare = service.compare_periods(
        current_from=date(2026, 1, 31),
        current_to=date(2026, 1, 31),
        prev_from=date(2026, 2, 1),
        prev_to=date(2026, 2, 1),
    )

    assert compare["current"]["total"] == 1
    assert compare["current"]["positives"] == 1
    assert compare["previous"]["total"] == 1
    assert compare["previous"]["positives"] == 0


def test_get_ismp_metrics_includes_admission_on_end_day(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "analytics_boundary_ismp.db")
    _seed_boundary_dataset(session_factory)
    service = AnalyticsService(session_factory=session_factory)

    result = service.get_ismp_metrics(date(2026, 1, 31), date(2026, 1, 31), department_id=None)

    assert result["total_cases"] == 1
    assert result["total_patient_days"] == 4
    assert result["ismp_total"] == 1
    assert result["ismp_cases"] == 1
    assert result["incidence"] == 1000.0
    assert result["incidence_density"] == 250.0
    assert result["prevalence"] == 100.0
