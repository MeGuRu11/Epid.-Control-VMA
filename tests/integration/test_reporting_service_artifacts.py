from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.services import reporting_service as reporting_service_module
from app.application.services.analytics_service import AnalyticsService
from app.application.services.reporting_service import ReportingService
from app.infrastructure.db.models_sqlalchemy import Base
from app.infrastructure.security.sha256 import sha256_file


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


def test_export_report_saves_artifact_and_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session_factory = make_session_factory(tmp_path / "reporting.db")
    monkeypatch.setattr(reporting_service_module, "REPORT_ARTIFACT_DIR", tmp_path / "artifacts")

    analytics_service = AnalyticsService(session_factory=session_factory)
    service = ReportingService(analytics_service=analytics_service, session_factory=session_factory)

    export_path = tmp_path / "analytics.xlsx"
    result = service.export_analytics_xlsx(
        request=AnalyticsSearchRequest(),
        file_path=export_path,
        actor_id=None,
    )

    assert export_path.exists()
    artifact_path = Path(str(result["artifact_path"]))
    assert artifact_path.exists()
    assert artifact_path != export_path
    assert str(result["sha256"]) == sha256_file(artifact_path)

    rows = service.list_report_runs(limit=10)
    assert len(rows) == 1
    assert rows[0]["artifact_path"] == str(artifact_path)

    verify = service.verify_report_run(int(rows[0]["id"]))
    assert verify["status"] == "ok"
    assert verify["verified"] is True


def test_verify_report_run_detects_hash_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session_factory = make_session_factory(tmp_path / "reporting_mismatch.db")
    monkeypatch.setattr(reporting_service_module, "REPORT_ARTIFACT_DIR", tmp_path / "artifacts")

    analytics_service = AnalyticsService(session_factory=session_factory)
    service = ReportingService(analytics_service=analytics_service, session_factory=session_factory)

    result = service.export_analytics_pdf(
        request=AnalyticsSearchRequest(),
        file_path=tmp_path / "analytics.pdf",
        actor_id=None,
    )
    artifact_path = Path(str(result["artifact_path"]))
    artifact_path.write_bytes(artifact_path.read_bytes() + b"tampered")

    rows = service.list_report_runs(limit=10)
    verify = service.verify_report_run(int(rows[0]["id"]))
    assert verify["status"] == "mismatch"
    assert verify["verified"] is False


def test_verify_report_run_detects_missing_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session_factory = make_session_factory(tmp_path / "reporting_missing.db")
    monkeypatch.setattr(reporting_service_module, "REPORT_ARTIFACT_DIR", tmp_path / "artifacts")

    analytics_service = AnalyticsService(session_factory=session_factory)
    service = ReportingService(analytics_service=analytics_service, session_factory=session_factory)

    service.export_analytics_xlsx(
        request=AnalyticsSearchRequest(),
        file_path=tmp_path / "analytics.xlsx",
        actor_id=None,
    )
    rows = service.list_report_runs(limit=10)
    artifact_path = Path(str(rows[0]["artifact_path"]))
    artifact_path.unlink()

    verify = service.verify_report_run(int(rows[0]["id"]))
    assert verify["status"] == "missing"
    assert verify["verified"] is False
