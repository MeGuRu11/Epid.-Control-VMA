from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.services.analytics_service import AnalyticsService
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.models_sqlalchemy import Base
from app.ui.analytics.controller import AnalyticsController


def _make_session_factory(db_path: Path) -> Callable[[], AbstractContextManager[Session]]:
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


def _seed_ris_dataset(session_factory: Callable[[], AbstractContextManager[Session]]) -> None:
    with session_factory() as session:
        icu = models.Department(name="ICU")
        surgery = models.Department(name="Surgery")
        material = models.RefMaterialType(code="BLOOD", name="Blood")
        eco = models.RefMicroorganism(code="ECO", name="E. coli")
        sau = models.RefMicroorganism(code="SAU", name="S. aureus")
        amx = models.RefAntibiotic(code="AMX", name="Amoxicillin")
        cip = models.RefAntibiotic(code="CIP", name="Ciprofloxacin")
        patient = models.Patient(
            full_name="Ivanov Ivan",
            dob=datetime(1990, 1, 1, tzinfo=UTC).date(),
            category="service",
        )
        session.add_all([icu, surgery, material, eco, sau, amx, cip, patient])
        session.flush()

        def _sample(index: int, department_id: int, micro_id: int, abx_id: int, ris: str) -> None:
            case = models.EmrCase(
                patient_id=patient.id,
                hospital_case_no=f"CASE-{index:03d}",
                department_id=department_id,
            )
            session.add(case)
            session.flush()
            sample = models.LabSample(
                patient_id=patient.id,
                emr_case_id=case.id,
                lab_no=f"LAB-{index:04d}",
                material_type_id=material.id,
                taken_at=datetime(2026, 5, index, tzinfo=UTC),
                growth_flag=1,
            )
            session.add(sample)
            session.flush()
            session.add(models.LabMicrobeIsolation(lab_sample_id=sample.id, microorganism_id=micro_id))
            session.add(models.LabAbxSusceptibility(lab_sample_id=sample.id, antibiotic_id=abx_id, ris=ris))

        for idx, (department_id, ris) in enumerate(
            [
                (icu.id, "R"),
                (icu.id, "R"),
                (icu.id, "S"),
                (surgery.id, "R"),
                (surgery.id, "I"),
            ],
            start=1,
        ):
            _sample(idx, cast(int, department_id), cast(int, eco.id), cast(int, amx.id), ris)
        _sample(6, cast(int, surgery.id), cast(int, sau.id), cast(int, cip.id), "S")


def _controller(service: AnalyticsService) -> AnalyticsController:
    return AnalyticsController(
        analytics_service=cast(Any, service),
        reference_service=cast(Any, object()),
        saved_filter_service=cast(Any, object()),
        reporting_service=cast(Any, object()),
    )


def test_search_samples_includes_ris_field(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "analytics_ris.db")
    _seed_ris_dataset(session_factory)
    service = AnalyticsService(session_factory=session_factory)

    rows = service.search_samples(AnalyticsSearchRequest())

    assert rows
    assert {row.ris for row in rows} == {"R", "S", "I"}


def test_controller_get_heatmap_data_groups_correctly(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "analytics_heatmap.db")
    _seed_ris_dataset(session_factory)
    controller = _controller(AnalyticsService(session_factory=session_factory))

    matrix, ordered_micros = controller.get_heatmap_data(AnalyticsSearchRequest())

    assert ordered_micros == ["ECO - E. coli", "SAU - S. aureus"]
    assert matrix["ICU"]["ECO - E. coli"] == 3
    assert matrix["Surgery"]["ECO - E. coli"] == 2
    assert matrix["Surgery"]["SAU - S. aureus"] == 1


def test_controller_get_resistance_data_calculates_percentages(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "analytics_resistance.db")
    _seed_ris_dataset(session_factory)
    controller = _controller(AnalyticsService(session_factory=session_factory))

    resistance = controller.get_resistance_data(AnalyticsSearchRequest())

    assert resistance["ECO - E. coli"]["AMX - Amoxicillin"] == {
        "S": 1,
        "I": 1,
        "R": 3,
        "total": 5,
    }
    assert resistance["SAU - S. aureus"]["CIP - Ciprofloxacin"] == {
        "S": 1,
        "I": 0,
        "R": 0,
        "total": 1,
    }
