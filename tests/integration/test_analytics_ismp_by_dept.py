from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.services.analytics_service import AnalyticsService
from app.domain.constants import IsmpType
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.models_sqlalchemy import Base


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


def _seed_ismp_by_department(session_factory: Callable[[], AbstractContextManager[Session]]) -> None:
    with session_factory() as session:
        icu = models.Department(name="ICU")
        surgery = models.Department(name="Surgery")
        therapy = models.Department(name="Therapy")
        patient = models.Patient(full_name="Patient A")
        session.add_all([icu, surgery, therapy, patient])
        session.flush()

        def _case(index: int, department_id: int) -> models.EmrCase:
            case = models.EmrCase(
                patient_id=cast(int, patient.id),
                hospital_case_no=f"CASE-{index:03d}",
                department_id=department_id,
            )
            session.add(case)
            session.flush()
            session.add(
                models.EmrCaseVersion(
                    emr_case_id=cast(int, case.id),
                    version_no=1,
                    valid_from=datetime(2026, 5, index, tzinfo=UTC),
                    is_current=True,
                    admission_date=datetime(2026, 5, index, tzinfo=UTC),
                    length_of_stay_days=7,
                )
            )
            return case

        cases = [
            _case(1, cast(int, icu.id)),
            _case(2, cast(int, icu.id)),
            _case(3, cast(int, surgery.id)),
            _case(4, cast(int, therapy.id)),
        ]
        session.add_all(
            [
                models.IsmpCase(
                    emr_case_id=cast(int, cases[0].id),
                    ismp_type=IsmpType.VAP.value,
                    start_date=date(2026, 5, 10),
                ),
                models.IsmpCase(
                    emr_case_id=cast(int, cases[0].id),
                    ismp_type=IsmpType.CA_BSI.value,
                    start_date=date(2026, 5, 11),
                ),
                models.IsmpCase(
                    emr_case_id=cast(int, cases[1].id),
                    ismp_type=IsmpType.SSI.value,
                    start_date=date(2026, 5, 12),
                ),
                models.IsmpCase(
                    emr_case_id=cast(int, cases[2].id),
                    ismp_type=IsmpType.VAP.value,
                    start_date=date(2026, 5, 13),
                ),
                models.IsmpCase(
                    emr_case_id=cast(int, cases[3].id),
                    ismp_type=IsmpType.VAP.value,
                    start_date=date(2026, 4, 1),
                ),
            ]
        )


def test_get_ismp_by_department_returns_sorted_list(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "ismp_by_department.db")
    _seed_ismp_by_department(session_factory)
    service = AnalyticsService(session_factory=session_factory)

    rows = service.get_ismp_by_department(date(2026, 5, 1), date(2026, 5, 31))

    assert rows == [("ICU", 3), ("Surgery", 1)]


def test_get_ismp_by_department_empty_when_no_ismp(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "ismp_by_department_empty.db")
    service = AnalyticsService(session_factory=session_factory)

    rows = service.get_ismp_by_department(date(2026, 5, 1), date(2026, 5, 31))

    assert rows == []
