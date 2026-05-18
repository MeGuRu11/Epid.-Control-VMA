from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.models_sqlalchemy import Base
from scripts.seed_demo_data import seed


def _make_session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{(tmp_path / 'seed_demo.db').as_posix()}", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
    return session_local()


def test_seed_demo_data_creates_analytics_dataset(tmp_path: Path) -> None:
    session = _make_session(tmp_path)
    try:
        stats = seed(session, id_store_path=tmp_path / "seed_demo_ids.json")
        session.commit()

        today = datetime.now(UTC).date()
        earliest = today - timedelta(days=90)

        assert stats.patients == 5
        assert stats.emr_cases == 15
        assert stats.lab_samples == 35
        assert stats.positive_lab_samples == 24
        assert stats.ismp_cases == 4
        assert stats.sanitary_samples == 8

        positive_samples = session.scalar(
            select(func.count(models.LabSample.id)).where(models.LabSample.growth_flag == 1)
        )
        abx_rows = session.scalar(select(func.count(models.LabAbxSusceptibility.id)))
        current_versions = session.scalar(
            select(func.count(models.EmrCaseVersion.id)).where(models.EmrCaseVersion.is_current == True)  # noqa: E712
        )

        assert positive_samples == stats.positive_lab_samples
        assert positive_samples is not None
        assert abx_rows is not None
        assert abx_rows >= positive_samples
        assert current_versions == stats.emr_cases

        sample_count_rows = session.execute(
            select(models.Patient.full_name, func.count(models.LabSample.id))
            .join(models.LabSample, models.LabSample.patient_id == models.Patient.id)
            .group_by(models.Patient.id, models.Patient.full_name)
        ).all()
        sample_counts_by_patient: dict[str, int] = {
            str(row.full_name): int(row[1]) for row in sample_count_rows
        }
        assert len(sample_counts_by_patient) == 5
        assert set(sample_counts_by_patient.values()) == {7}

        departments_with_samples = set(
            session.scalars(
                select(models.Department.name)
                .select_from(models.LabSample)
                .join(models.EmrCase, models.EmrCase.id == models.LabSample.emr_case_id)
                .join(models.Department, models.Department.id == models.EmrCase.department_id)
                .group_by(models.Department.name)
            ).all()
        )
        assert departments_with_samples == {"Реанимация (ОРИТ)", "Хирургия", "Терапия", "Неврология"}

        ris_values = set(session.scalars(select(models.LabAbxSusceptibility.ris)).all())
        assert ris_values == {"R", "I", "S"}

        first_sample_date = session.scalar(select(func.min(models.LabSample.taken_at)))
        last_ismp_date = session.scalar(select(func.max(models.IsmpCase.start_date)))

        assert first_sample_date is not None
        assert first_sample_date.date() >= earliest
        assert last_ismp_date is not None
        assert earliest <= last_ismp_date <= today
    finally:
        session.close()


def test_seed_clear_removes_only_demo_data(tmp_path: Path) -> None:
    session = _make_session(tmp_path)
    id_store = tmp_path / "seed_demo_ids.json"
    try:
        seed(session, id_store_path=id_store)
        session.flush()

        department = session.scalar(select(models.Department).where(models.Department.name == "Терапия"))
        material = session.scalar(select(models.RefMaterialType).where(models.RefMaterialType.code == "BLD"))
        assert department is not None
        assert material is not None

        real_patient = models.Patient(
            full_name="Контрольный Пациент",
            dob=datetime(1980, 1, 1, tzinfo=UTC).date(),
            sex="M",
            category="real",
        )
        session.add(real_patient)
        session.flush()
        real_case = models.EmrCase(
            patient_id=real_patient.id,
            hospital_case_no="REAL-CASE-001",
            department_id=department.id,
        )
        session.add(real_case)
        session.flush()
        real_sample = models.LabSample(
            patient_id=real_patient.id,
            emr_case_id=real_case.id,
            lab_no="REAL-LAB-001",
            material_type_id=material.id,
            taken_at=datetime(2026, 5, 11, 9, 0, tzinfo=UTC),
            growth_flag=0,
        )
        session.add(real_sample)
        session.flush()

        stats = seed(session, clear=True, id_store_path=id_store)
        session.flush()

        demo_labs = session.scalar(
            select(func.count(models.LabSample.id)).where(models.LabSample.lab_no.like("DEMO-%"))
        )
        real_labs = session.scalar(
            select(func.count(models.LabSample.id)).where(models.LabSample.lab_no == "REAL-LAB-001")
        )
        real_patients = session.scalar(
            select(func.count(models.Patient.id)).where(models.Patient.full_name == "Контрольный Пациент")
        )

        assert demo_labs == stats.lab_samples == 35
        assert real_labs == 1
        assert real_patients == 1
        assert id_store.exists()
    finally:
        session.close()
