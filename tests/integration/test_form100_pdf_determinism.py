from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.services import reporting_service as reporting_service_module
from app.application.services.analytics_service import AnalyticsService
from app.application.services.reporting_service import ReportingService
from app.infrastructure.db.models_sqlalchemy import Base
from app.infrastructure.reporting.form100_pdf_report_v2 import export_form100_pdf_v2


class _FixedDateTime:
    @classmethod
    def now(cls, tz: Any = None) -> datetime:
        fixed = datetime(2026, 5, 8, 9, 30, 0, tzinfo=UTC)
        if tz is None:
            return fixed.replace(tzinfo=None)
        return fixed.astimezone(tz)


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


def _make_form100_payload() -> dict[str, Any]:
    return {
        "id": "deterministic-card",
        "version": 2,
        "status": "SIGNED",
        "birth_date": "1991-05-06",
        "signed_by": "doctor",
        "signed_at": "2026-05-08T09:00:00+00:00",
        "data": {
            "main": {
                "main_full_name": "Иванов Иван Иванович",
                "main_rank": "капитан",
                "main_unit": "в/ч 12345",
                "main_id_tag": "Ж-100",
                "main_injury_date": "03.03.2026",
                "main_injury_time": "11:45",
            },
            "bottom": {
                "main_diagnosis": "Огнестрельное ранение",
                "doctor_signature": "д-р Петров",
            },
            "flags": {
                "flag_emergency": True,
                "flag_radiation": False,
                "flag_sanitation": False,
            },
            "medical_help": {
                "mp_antibiotic": True,
                "mp_antibiotic_dose": "цефазолин 1 г",
                "mp_analgesic": True,
                "mp_analgesic_dose": "кеторолак 30 мг",
            },
            "bodymap_gender": "M",
            "bodymap_annotations": [],
            "bodymap_tissue_types": ["мягкие ткани"],
        },
    }


def test_form100_pdf_is_byte_identical_for_same_payload(tmp_path: Path) -> None:
    """Два вызова Form100 PDF на одном payload дают одинаковые байты."""
    pdf_a = tmp_path / "form100_a.pdf"
    pdf_b = tmp_path / "form100_b.pdf"

    export_form100_pdf_v2(card=_make_form100_payload(), file_path=pdf_a)
    export_form100_pdf_v2(card=_make_form100_payload(), file_path=pdf_b)

    assert pdf_a.read_bytes() == pdf_b.read_bytes()


def test_analytics_pdf_is_byte_identical_for_same_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Два вызова analytics PDF на одном request дают одинаковые байты."""
    session_factory = _make_session_factory(tmp_path / "analytics_pdf_determinism.db")
    monkeypatch.setattr(reporting_service_module, "REPORT_ARTIFACT_DIR", tmp_path / "artifacts")
    monkeypatch.setattr(reporting_service_module, "datetime", _FixedDateTime)

    service = ReportingService(
        analytics_service=AnalyticsService(session_factory=session_factory),
        session_factory=session_factory,
    )
    request = AnalyticsSearchRequest()
    pdf_a = tmp_path / "analytics_a.pdf"
    pdf_b = tmp_path / "analytics_b.pdf"

    service.export_analytics_pdf(request=request, file_path=pdf_a, actor_id=None)
    service.export_analytics_pdf(request=request, file_path=pdf_b, actor_id=None)

    assert pdf_a.read_bytes() == pdf_b.read_bytes()
