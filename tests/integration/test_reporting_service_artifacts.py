from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from reportlab.platypus import PageBreak, Paragraph, Table
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


def _plain_texts(elements: list[Any]) -> list[str]:
    texts: list[str] = []
    for element in elements:
        if isinstance(element, Paragraph):
            texts.append(element.getPlainText())
        elif isinstance(element, Table):
            for row in element._cellvalues:  # noqa: SLF001 - ReportLab stores cell content internally.
                for cell in row:
                    if isinstance(cell, Paragraph | Table):
                        texts.extend(_plain_texts([cell]))
                    else:
                        texts.append(str(cell))
    return texts


def _capture_pdf_elements(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Any]]:
    captured: dict[str, list[Any]] = {}

    def _capture_build(doc: Any, elements: list[Any]) -> None:
        captured["elements"] = elements
        Path(doc.filename).write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(reporting_service_module, "build_invariant_pdf", _capture_build)
    return captured


def test_export_report_saves_artifact_and_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session_factory = make_session_factory(tmp_path / "reporting.db")
    monkeypatch.setattr(reporting_service_module, "REPORT_ARTIFACT_DIR", tmp_path / "artifacts")

    analytics_service = AnalyticsService(session_factory=session_factory)
    service = ReportingService(analytics_service=analytics_service, session_factory=session_factory)

    export_path = tmp_path / "analytics.xlsx"
    result = service.export_analytics_xlsx(
        request=AnalyticsSearchRequest(
            patient_name="Иванов И.И.",
            lab_no="LAB-001",
            search_text="стафилококк",
            department_id=1,
        ),
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
    assert rows[0]["filters"]["patient_name"] == "***"
    assert rows[0]["filters"]["lab_no"] == "***"
    assert rows[0]["filters"]["search_text"] == "***"
    assert rows[0]["filters"]["department_id"] == 1

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


@pytest.mark.parametrize(
    ("export_method_name", "file_name"),
    [
        ("export_analytics_xlsx", "dated_analytics.xlsx"),
        ("export_analytics_pdf", "dated_analytics.pdf"),
    ],
)
def test_export_report_accepts_date_filters_in_history_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    export_method_name: str,
    file_name: str,
) -> None:
    session_factory = make_session_factory(tmp_path / f"{export_method_name}.db")
    monkeypatch.setattr(reporting_service_module, "REPORT_ARTIFACT_DIR", tmp_path / "artifacts")

    analytics_service = AnalyticsService(session_factory=session_factory)
    service = ReportingService(analytics_service=analytics_service, session_factory=session_factory)
    export_method = getattr(service, export_method_name)

    result = export_method(
        request=AnalyticsSearchRequest(
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 19),
            department_id=1,
        ),
        file_path=tmp_path / file_name,
        actor_id=None,
    )

    assert Path(str(result["artifact_path"])).exists()

    rows = service.list_report_runs(limit=10)
    assert len(rows) == 1
    assert rows[0]["filters"]["date_from"] == "2026-04-01"
    assert rows[0]["filters"]["date_to"] == "2026-04-19"


def test_export_analytics_pdf_contains_all_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = make_session_factory(tmp_path / "pdf_sections.db")
    monkeypatch.setattr(reporting_service_module, "REPORT_ARTIFACT_DIR", tmp_path / "artifacts")
    captured = _capture_pdf_elements(monkeypatch)

    analytics_service = AnalyticsService(session_factory=session_factory)
    service = ReportingService(analytics_service=analytics_service, session_factory=session_factory)

    export_path = tmp_path / "analytics_v2.pdf"
    result = service.export_analytics_pdf(
        request=AnalyticsSearchRequest(),
        file_path=export_path,
        actor_id=None,
    )

    elements = captured["elements"]
    text = "\n".join(_plain_texts(elements))
    assert export_path.exists()
    assert str(result["path"]) == str(export_path)
    assert sum(isinstance(element, PageBreak) for element in elements) == 6
    assert "Аналитический отчёт по пробам" in text
    assert "ИСМП — Инфекции, связанные с оказанием медицинской помощи" in text
    assert "Сводка по отделениям" in text
    assert "Топ микроорганизмов" in text
    assert "Паттерн резистентности" in text
    assert "Heatmap: отделения × микроорганизмы" in text
    assert "Тренд по периодам" in text
    assert "Таблица проб" in text


def test_export_analytics_pdf_with_resistance_and_heatmap_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.infrastructure.db.models_sqlalchemy import (
        Department,
        EmrCase,
        LabAbxSusceptibility,
        LabMicrobeIsolation,
        LabSample,
        Patient,
        RefAntibiotic,
        RefMaterialType,
        RefMicroorganism,
    )

    session_factory = make_session_factory(tmp_path / "pdf_data.db")
    monkeypatch.setattr(reporting_service_module, "REPORT_ARTIFACT_DIR", tmp_path / "artifacts")
    captured = _capture_pdf_elements(monkeypatch)

    with session_factory() as session:
        dept = Department(name="Терапия")
        material = RefMaterialType(code="BLD", name="Кровь")
        micro = RefMicroorganism(name="E.coli", code="ECO")
        antibiotic = RefAntibiotic(name="Ампициллин", code="AMP")
        patient = Patient(full_name="Иванов И.И.", dob=date(1980, 1, 1), category="Военнослужащий")
        session.add_all([dept, material, micro, antibiotic, patient])
        session.flush()

        case = EmrCase(patient_id=patient.id, hospital_case_no="CASE-1", department_id=dept.id)
        session.add(case)
        session.flush()

        sample = LabSample(
            patient_id=patient.id,
            emr_case_id=case.id,
            lab_no="LAB-001",
            material_type_id=material.id,
            taken_at=datetime(2024, 3, 1, 8, 30, tzinfo=UTC),
            growth_flag=1,
        )
        session.add(sample)
        session.flush()

        session.add_all(
            [
                LabMicrobeIsolation(lab_sample_id=sample.id, microorganism_id=micro.id),
                LabAbxSusceptibility(
                    lab_sample_id=sample.id,
                    antibiotic_id=antibiotic.id,
                    ris="R",
                ),
            ]
        )

    analytics_service = AnalyticsService(session_factory=session_factory)
    service = ReportingService(analytics_service=analytics_service, session_factory=session_factory)
    export_path = tmp_path / "analytics_v2_data.pdf"
    result = service.export_analytics_pdf(
        request=AnalyticsSearchRequest(),
        file_path=export_path,
        actor_id=None,
    )

    text = "\n".join(_plain_texts(captured["elements"]))
    assert export_path.exists()
    assert str(result["path"]) == str(export_path)
    assert "Терапия" in text
    assert "ECO - E.coli" in text
    assert "AMP - Ампициллин" in text
    assert "R:1 I:0 S:0" in text
