from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from reportlab.platypus import KeepTogether

from app.application.services import form100_service_v2 as form100_service_module
from app.application.services.form100_service_v2 import Form100ServiceV2
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.reporting import form100_pdf_report_v2 as report_module
from tests.integration.test_form100_v2_service import (
    make_create_request,
    make_session_factory,
    seed_users,
)


def _plain_texts(elements: list[Any]) -> list[str]:
    texts: list[str] = []

    def _walk(value: Any) -> None:
        if hasattr(value, "getPlainText"):
            texts.append(str(value.getPlainText()))
            return
        content = getattr(value, "_content", None)
        if isinstance(content, list):
            for item in content:
                _walk(item)
        cellvalues = getattr(value, "_cellvalues", None)
        if isinstance(cellvalues, list):
            for row in cellvalues:
                if isinstance(row, list):
                    for cell in row:
                        _walk(cell)
                else:
                    _walk(row)

    for element in elements:
        _walk(element)
    return texts


def _capture_elements(
    card: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> list[Any]:
    captured: dict[str, list[Any]] = {}

    def _capture(_doc: Any, elements: list[Any]) -> None:
        captured["elements"] = elements

    monkeypatch.setattr(report_module, "build_invariant_pdf", _capture)
    report_module.export_form100_pdf_v2(card=card, file_path=tmp_path / "form100.pdf")
    return captured["elements"]


def _pdf_text(card: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    return "\n".join(_plain_texts(_capture_elements(card, tmp_path, monkeypatch)))


def _card_payload(*, emr_context: dict[str, Any] | None = None) -> dict[str, Any]:
    card: dict[str, Any] = {
        "id": "96e79a85-c246-4963-8282-02f5672777cf",
        "version": 3,
        "signed_version": 2,
        "status": "SIGNED",
        "birth_date": "1992-02-02T00:00:00+00:00",
        "signed_by": "Synthetic signer",
        "signed_at": datetime(2026, 5, 6, 7, 14, 44, 623119, tzinfo=UTC),
        "data": {
            "main": {
                "main_full_name": "Synthetic Patient",
                "main_rank": "captain",
                "main_unit": "1st unit",
                "main_id_tag": "A12345",
                "main_injury_date": "2026-04-01",
                "main_injury_time": "09:00",
            },
            "lesion": {"lesion_gunshot": True},
            "bottom": {
                "main_diagnosis": "Synthetic diagnosis",
                "doctor_signature": "Synthetic signer",
            },
            "medical_help": {
                "mp_antibiotic": None,
                "mp_analgesic": False,
                "mp_surgical_intervention": True,
                "mp_surgical_intervention_details": "Debridement",
            },
            "flags": {"flag_emergency": True, "flag_radiation": False, "flag_sanitation": False},
            "bodymap_gender": "M",
            "bodymap_annotations": [
                {
                    "annotation_type": "WOUND_X",
                    "x": 0.72,
                    "y": 0.36,
                    "silhouette": "male_front",
                    "note": "Synthetic marker",
                    "shape_json": {},
                }
            ],
            "bodymap_tissue_types": ["soft tissue"],
        },
    }
    if emr_context is not None:
        card["emr_context"] = emr_context
    return card


def test_pdf_birth_date_is_dd_mm_yyyy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text = _pdf_text(_card_payload(), tmp_path, monkeypatch)

    assert "02.02.1992" in text
    assert "1992-02-02" not in text


def test_pdf_signed_date_no_microseconds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text = _pdf_text(_card_payload(), tmp_path, monkeypatch)

    assert "06.05.2026 07:14" in text
    assert "623119" not in text


def test_pdf_no_isoformat_dates_anywhere(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text = _pdf_text(_card_payload(), tmp_path, monkeypatch)

    assert "1992-02-02" not in text
    assert "2026-05-06" not in text


def test_pdf_annotation_type_no_empty_parens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text = _pdf_text(_card_payload(), tmp_path, monkeypatch)

    assert "Рана" in text
    assert "Рана (" not in text


def test_pdf_bodymap_table_has_proektsiya_column(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text = _pdf_text(_card_payload(), tmp_path, monkeypatch)

    assert "Проекция" in text
    assert "Спереди" in text


def test_pdf_bodymap_table_has_storona_column(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text = _pdf_text(_card_payload(), tmp_path, monkeypatch)

    assert "Сторона тела" in text
    assert "Правая" in text


def test_pdf_bodymap_location_is_human_readable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text = _pdf_text(_card_payload(), tmp_path, monkeypatch)

    assert "грудь, правая сторона" in text
    assert "X=0.72" not in text


def test_pdf_uses_reviziya_not_versiya_in_footer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text = _pdf_text(_card_payload(), tmp_path, monkeypatch)

    assert "Ревизия: 2" in text
    assert "Версия:" not in text


def test_pdf_emr_context_block_shown_when_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text = _pdf_text(
        _card_payload(
            emr_context={
                "hospital_case_no": "EMR-42",
                "department_name": "Surgery",
                "admission_date": datetime(2026, 5, 1, 8, 30, tzinfo=UTC),
                "injury_date": datetime(2026, 4, 30, 22, 15, tzinfo=UTC),
            }
        ),
        tmp_path,
        monkeypatch,
    )

    assert "Связанная госпитализация" in text
    assert "Номер ЭМЗ" in text
    assert "EMR-42" in text
    assert "Отделение" in text
    assert "Surgery" in text
    assert "01.05.2026 08:30" in text
    assert "30.04.2026 22:15" in text


def test_pdf_emr_context_block_hidden_when_no_emr_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text = _pdf_text(_card_payload(emr_context={}), tmp_path, monkeypatch)

    assert "Связанная госпитализация" not in text


def test_pdf_medical_help_distinguishes_unset_and_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = _pdf_text(_card_payload(), tmp_path, monkeypatch)

    assert "не указано" in text
    assert "Нет" in text


def test_pdf_keeps_bodymap_heading_with_bodymap_flowable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    elements = _capture_elements(_card_payload(), tmp_path, monkeypatch)

    assert any(
        isinstance(element, KeepTogether) and "4. Схема тела" in "\n".join(_plain_texts([element]))
        for element in elements
    )


def test_form100_service_export_pdf_adds_emr_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = make_session_factory(tmp_path / "form100_pdf_emr_context.db")
    _admin_id, operator_id = seed_users(session_factory)
    with session_factory() as session:
        department = models.Department(name="Surgery")
        patient = models.Patient(full_name="Synthetic Patient", sex="M")
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
        emr_case_id = cast(int, emr_case.id)

    captured: dict[str, dict[str, Any]] = {}

    def _capture_pdf(*, card: dict[str, Any], file_path: str | Path) -> None:
        captured["card"] = card
        Path(file_path).write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(form100_service_module, "export_form100_pdf_v2", _capture_pdf)

    service = Form100ServiceV2(session_factory=session_factory)
    request = make_create_request().model_copy(update={"emr_case_id": emr_case_id})
    created = service.create_card(request, actor_id=operator_id)

    service.export_pdf(created.id, tmp_path / "form100.pdf", actor_id=operator_id)

    emr_context = captured["card"].get("emr_context")
    assert emr_context == {
        "hospital_case_no": "EMR-42",
        "department_name": "Surgery",
        "admission_date": datetime(2026, 5, 1, 8, 30, tzinfo=UTC).replace(tzinfo=None),
        "injury_date": datetime(2026, 4, 30, 22, 15, tzinfo=UTC).replace(tzinfo=None),
    }
