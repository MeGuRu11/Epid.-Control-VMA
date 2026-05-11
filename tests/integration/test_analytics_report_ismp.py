from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.services import reporting_service as reporting_service_module
from app.application.services.analytics_service import AnalyticsService
from app.application.services.reporting_service import ReportingService
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


@pytest.fixture
def seeded_db_with_ismp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[], AbstractContextManager[Session]]:
    session_factory = _make_session_factory(tmp_path / "analytics_report_ismp.db")
    monkeypatch.setattr(reporting_service_module, "REPORT_ARTIFACT_DIR", tmp_path / "artifacts")
    with session_factory() as session:
        department = models.Department(name="ICU")
        patient_a = models.Patient(full_name="Patient A")
        patient_b = models.Patient(full_name="Patient B")
        session.add_all([department, patient_a, patient_b])
        session.flush()

        case_a = models.EmrCase(
            patient_id=cast(int, patient_a.id),
            hospital_case_no="CASE-ISMP-1",
            department_id=cast(int, department.id),
        )
        case_b = models.EmrCase(
            patient_id=cast(int, patient_b.id),
            hospital_case_no="CASE-ISMP-2",
            department_id=cast(int, department.id),
        )
        session.add_all([case_a, case_b])
        session.flush()

        session.add_all(
            [
                models.EmrCaseVersion(
                    emr_case_id=cast(int, case_a.id),
                    version_no=1,
                    valid_from=datetime(2026, 5, 1, tzinfo=UTC),
                    is_current=True,
                    admission_date=datetime(2026, 5, 1, tzinfo=UTC),
                    length_of_stay_days=10,
                ),
                models.EmrCaseVersion(
                    emr_case_id=cast(int, case_b.id),
                    version_no=1,
                    valid_from=datetime(2026, 5, 2, tzinfo=UTC),
                    is_current=True,
                    admission_date=datetime(2026, 5, 2, tzinfo=UTC),
                    length_of_stay_days=20,
                ),
            ]
        )
        session.add_all(
            [
                models.IsmpCase(
                    emr_case_id=cast(int, case_a.id),
                    ismp_type=IsmpType.VAP.value,
                    start_date=date(2026, 5, 3),
                ),
                models.IsmpCase(
                    emr_case_id=cast(int, case_a.id),
                    ismp_type=IsmpType.CA_BSI.value,
                    start_date=date(2026, 5, 4),
                ),
                models.IsmpCase(
                    emr_case_id=cast(int, case_b.id),
                    ismp_type=IsmpType.SSI.value,
                    start_date=date(2026, 5, 5),
                ),
            ]
        )
    return session_factory


def _reporting_service(session_factory: Callable[[], AbstractContextManager[Session]]) -> ReportingService:
    analytics_service = AnalyticsService(session_factory=session_factory)
    return ReportingService(analytics_service=analytics_service, session_factory=session_factory)


def test_report_run_summary_includes_ismp_fields(
    seeded_db_with_ismp: Callable[[], AbstractContextManager[Session]],
    tmp_path: Path,
) -> None:
    service = _reporting_service(seeded_db_with_ismp)

    result = service.export_analytics_xlsx(
        AnalyticsSearchRequest(date_from=date(2026, 5, 1), date_to=date(2026, 5, 31)),
        tmp_path / "analytics.xlsx",
        actor_id=None,
    )

    with seeded_db_with_ismp() as session:
        row = session.get(models.ReportRun, int(result["report_run_id"]))
        assert row is not None
        summary = json.loads(str(row.result_summary_json))

    assert summary["ismp_cases"] == 2
    assert summary["ismp_incidence"] == 1000.0
    assert summary["ismp_incidence_density"] == 100.0
    assert summary["ismp_prevalence"] == 100.0
    assert sorted(summary["ismp_by_type"], key=lambda item: str(item["type"])) == sorted(
        [
            {"type": IsmpType.CA_BSI.value, "count": 1},
            {"type": IsmpType.SSI.value, "count": 1},
            {"type": IsmpType.VAP.value, "count": 1},
        ],
        key=lambda item: str(item["type"]),
    )


def test_ismp_metrics_in_report_match_service_output(
    seeded_db_with_ismp: Callable[[], AbstractContextManager[Session]],
    tmp_path: Path,
) -> None:
    analytics_service = AnalyticsService(session_factory=seeded_db_with_ismp)
    reporting_service = ReportingService(analytics_service=analytics_service, session_factory=seeded_db_with_ismp)
    request = AnalyticsSearchRequest(date_from=date(2026, 5, 1), date_to=date(2026, 5, 31))
    expected = analytics_service.get_ismp_metrics(request.date_from, request.date_to, request.department_id)

    result = reporting_service.export_analytics_pdf(request, tmp_path / "analytics.pdf", actor_id=None)

    with seeded_db_with_ismp() as session:
        row = session.execute(
            select(models.ReportRun).where(models.ReportRun.id == int(result["report_run_id"]))
        ).scalar_one()
        summary = json.loads(str(row.result_summary_json))

    assert summary["ismp_cases"] == expected["ismp_cases"]
    assert summary["ismp_incidence"] == expected["incidence"]
    assert summary["ismp_incidence_density"] == expected["incidence_density"]
    assert summary["ismp_prevalence"] == expected["prevalence"]
    assert summary["ismp_by_type"] == expected["by_type"]
