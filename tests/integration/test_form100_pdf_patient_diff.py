from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from app.application.services.form100_service_v2 import Form100ServiceV2
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.reporting import form100_pdf_report_v2 as report_module
from tests.integration.test_form100_pdf_layout import _plain_texts
from tests.integration.test_form100_v2_service import (
    make_create_request,
    make_session_factory,
    seed_users,
)


def _seed_patient_case(
    session_factory: Any,
    *,
    full_name: str,
    dob: date = date(1990, 1, 1),
) -> int:
    with session_factory() as session:
        department = models.Department(name="Хирургия")
        patient = models.Patient(full_name=full_name, dob=dob, sex="M")
        session.add_all([department, patient])
        session.flush()
        emr_case = models.EmrCase(
            patient_id=cast(int, patient.id),
            hospital_case_no="EMR-42",
            department_id=cast(int, department.id),
        )
        session.add(emr_case)
        session.flush()
        session.add(
            models.EmrCaseVersion(
                emr_case_id=cast(int, emr_case.id),
                version_no=1,
                valid_from=datetime(2026, 5, 1, 8, 30, tzinfo=UTC),
                is_current=True,
                admission_date=datetime(2026, 5, 1, 8, 30, tzinfo=UTC),
                injury_date=datetime(2026, 4, 30, 22, 15, tzinfo=UTC),
            )
        )
        return cast(int, emr_case.id)


def _export_pdf_text(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    patient_full_name: str,
    card_full_name: str,
) -> str:
    session_factory = make_session_factory(tmp_path / f"{card_full_name}.db")
    _admin_id, operator_id = seed_users(session_factory)
    emr_case_id = _seed_patient_case(session_factory, full_name=patient_full_name)
    service = Form100ServiceV2(session_factory=session_factory)
    created = service.create_card(
        make_create_request().model_copy(
            update={
                "emr_case_id": emr_case_id,
                "main_full_name": card_full_name,
            }
        ),
        actor_id=operator_id,
    )
    captured: dict[str, list[Any]] = {}

    def _capture(doc: Any, elements: list[Any]) -> None:
        captured["elements"] = elements
        Path(str(doc.filename)).write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(report_module, "build_invariant_pdf", _capture)

    service.export_pdf(created.id, tmp_path / "form100.pdf", actor_id=operator_id)

    return "\n".join(_plain_texts(captured["elements"]))


def test_pdf_shows_patient_name_diff_in_emr_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = _export_pdf_text(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        patient_full_name="Иванов Иван Иванович",
        card_full_name="Петров Пётр Петрович",
    )

    assert "Связанная госпитализация" in text
    assert "ФИО пациента в ЭМЗ" in text
    assert "Иванов Иван Иванович" in text
    assert "Отличается от ФИО в карточке" in text


def test_pdf_no_diff_marker_when_names_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = _export_pdf_text(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        patient_full_name="Иванов Иван Иванович",
        card_full_name="Иванов Иван Иванович",
    )

    assert "Связанная госпитализация" in text
    assert "Отличается от ФИО в карточке" not in text
