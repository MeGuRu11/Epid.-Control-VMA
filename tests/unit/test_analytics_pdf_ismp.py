from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import Any, cast

from reportlab.platypus import Paragraph, Table
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.services import reporting_service as reporting_service_module
from app.application.services.reporting_service import ReportingService
from app.infrastructure.db.models_sqlalchemy import Base


class _AnalyticsServiceStub:
    def __init__(self, *, ismp: dict[str, Any]) -> None:
        self.ismp = ismp

    def search_samples(self, _request: AnalyticsSearchRequest) -> list[Any]:
        return []

    def get_aggregates(self, _request: AnalyticsSearchRequest) -> dict[str, Any]:
        return {"total": 0, "positives": 0, "positive_share": 0.0}

    def get_ismp_metrics(
        self,
        *,
        date_from: object,
        date_to: object,
        department_id: object,
    ) -> dict[str, Any]:
        return self.ismp


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


def _plain_texts(elements: list[Any]) -> list[str]:
    texts: list[str] = []
    for element in elements:
        if isinstance(element, Paragraph):
            texts.append(element.getPlainText())
        elif isinstance(element, Table):
            for row in element._cellvalues:  # noqa: SLF001 - ReportLab exposes table content only internally.
                for cell in row:
                    texts.extend(_plain_texts([cell]) if isinstance(cell, Paragraph | Table) else [str(cell)])
    return texts


def _capture_pdf_text(tmp_path: Path, monkeypatch: Any, ismp: dict[str, Any]) -> str:
    session_factory = _make_session_factory(tmp_path / "analytics_pdf_ismp.db")
    reporting_service_module.REPORT_ARTIFACT_DIR = tmp_path / "artifacts"
    captured: dict[str, list[Any]] = {}

    def _capture_build(_doc: Any, elements: list[Any]) -> None:
        captured["elements"] = elements
        Path(_doc.filename).write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(reporting_service_module, "build_invariant_pdf", _capture_build)
    service = ReportingService(
        analytics_service=cast(Any, _AnalyticsServiceStub(ismp=ismp)),
        session_factory=session_factory,
    )
    service.export_analytics_pdf(AnalyticsSearchRequest(), tmp_path / "analytics.pdf", actor_id=None)
    return "\n".join(_plain_texts(captured["elements"]))


def _ismp_payload(*, ismp_cases: int = 2) -> dict[str, Any]:
    return {
        "total_cases": 4,
        "total_patient_days": 20,
        "ismp_total": 3 if ismp_cases else 0,
        "ismp_cases": ismp_cases,
        "incidence": 500.0 if ismp_cases else 0.0,
        "incidence_density": 150.0 if ismp_cases else 0.0,
        "prevalence": 50.0 if ismp_cases else 0.0,
        "by_type": [
            {"type": "ВАП", "count": 2},
            {"type": "КА-ИК", "count": 1},
        ]
        if ismp_cases
        else [],
    }


def test_analytics_pdf_contains_ismp_section(tmp_path: Path, monkeypatch: Any) -> None:
    text = _capture_pdf_text(tmp_path, monkeypatch, _ismp_payload())

    assert "ИСМП — Инфекции, связанные с оказанием медицинской помощи" in text


def test_analytics_pdf_ismp_shows_incidence_density_prevalence(tmp_path: Path, monkeypatch: Any) -> None:
    text = _capture_pdf_text(tmp_path, monkeypatch, _ismp_payload())

    assert "Инцидентность (на 1000 госпит.)" in text
    assert "Плотность (на 1000 койко-дн.)" in text
    assert "Превалентность" in text
    assert "50.0%" in text


def test_analytics_pdf_ismp_table_has_types_breakdown(tmp_path: Path, monkeypatch: Any) -> None:
    text = _capture_pdf_text(tmp_path, monkeypatch, _ismp_payload())

    assert "Разбивка по типам ИСМП:" in text
    assert "ВАП" in text
    assert "66.7%" in text
    assert "КА-ИК" in text
    assert "33.3%" in text


def test_analytics_pdf_ismp_empty_period_shows_placeholder(tmp_path: Path, monkeypatch: Any) -> None:
    text = _capture_pdf_text(tmp_path, monkeypatch, _ismp_payload(ismp_cases=0))

    assert "Случаев ИСМП в выбранном периоде не зарегистрировано." in text
