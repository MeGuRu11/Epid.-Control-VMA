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
        stats = seed(session)
        session.commit()

        today = datetime.now(UTC).date()
        earliest = today - timedelta(days=90)

        assert 5 <= stats.patients <= 8
        assert 10 <= stats.emr_cases <= 15
        assert 20 <= stats.lab_samples <= 30
        assert 3 <= stats.ismp_cases <= 5
        assert 5 <= stats.sanitary_samples <= 10

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

        first_sample_date = session.scalar(select(func.min(models.LabSample.taken_at)))
        last_ismp_date = session.scalar(select(func.max(models.IsmpCase.start_date)))

        assert first_sample_date is not None
        assert first_sample_date.date() >= earliest
        assert last_ismp_date is not None
        assert earliest <= last_ismp_date <= today
    finally:
        session.close()
