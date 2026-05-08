from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from app.application.dto.form100_v2_dto import (
    Form100CreateV2Request,
    Form100DataV2Dto,
    Form100SignV2Request,
)
from app.application.services.form100_service_v2 import Form100ServiceV2
from app.domain.rules.form100_rules_v2 import Form100SigningError
from app.infrastructure.db import models_sqlalchemy as models
from tests.integration.test_form100_v2_service import (
    make_create_request,
    make_session_factory,
    seed_users,
)


def _draft_with_missing_signing_fields() -> Form100CreateV2Request:
    return Form100CreateV2Request(
        main_full_name="Draft Patient",
        main_unit="Unit 100",
        main_id_tag="TAG-DRAFT",
        main_diagnosis="Draft diagnosis",
        birth_date=datetime(1991, 2, 3, tzinfo=UTC).date(),
        data=Form100DataV2Dto.model_validate(
            {
                "main": {
                    "main_full_name": "Draft Patient",
                    "main_unit": "Unit 100",
                    "main_id_tag": "TAG-DRAFT",
                    "birth_date": "1991-02-03",
                },
                "bottom": {"main_diagnosis": "Draft diagnosis"},
                "medical_help": {"mp_antibiotic": False, "mp_analgesic": False},
                "flags": {"flag_emergency": True, "flag_radiation": False, "flag_sanitation": False},
                "bodymap_gender": "M",
                "bodymap_annotations": [],
                "bodymap_tissue_types": [],
            }
        ),
    )


def _with_main_field(request: Form100CreateV2Request, field: str, value: object) -> Form100CreateV2Request:
    data = cast(dict[str, Any], request.data.model_dump())
    main = cast(dict[str, Any], dict(data.get("main") or {}))
    main[field] = value
    data["main"] = main
    return request.model_copy(update={"data": Form100DataV2Dto.model_validate(data)})


def test_draft_with_empty_optional_signing_fields_can_be_saved(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100_signing_draft.db")
    _admin_id, operator_id = seed_users(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)

    created = service.create_card(_draft_with_missing_signing_fields(), actor_id=operator_id)

    assert created.status == "DRAFT"
    assert created.version == 1


def test_sign_collects_all_errors_at_once(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100_signing_errors.db")
    _admin_id, operator_id = seed_users(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)
    created = service.create_card(_draft_with_missing_signing_fields(), actor_id=operator_id)

    with pytest.raises(Form100SigningError) as exc_info:
        service.sign_card(
            created.id,
            Form100SignV2Request(signed_by="doctor"),
            actor_id=operator_id,
            expected_version=created.version,
        )

    fields = {error.field for error in exc_info.value.errors}
    assert {
        "main.main_rank",
        "main.main_injury_date",
        "main.main_injury_time",
        "lesion_or_san_loss",
        "bottom.evacuation_priority",
    }.issubset(fields)
    message = str(exc_info.value)
    assert "main.main_rank" in message
    assert "bottom.evacuation_priority" in message


def test_sign_with_missing_injury_date_fails(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100_signing_missing_injury.db")
    _admin_id, operator_id = seed_users(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)
    request = _with_main_field(make_create_request(), "main_injury_date", "")
    created = service.create_card(request, actor_id=operator_id)

    with pytest.raises(Form100SigningError) as exc_info:
        service.sign_card(
            created.id,
            Form100SignV2Request(signed_by="doctor"),
            actor_id=operator_id,
            expected_version=created.version,
        )

    assert {error.field for error in exc_info.value.errors} == {"main.main_injury_date"}


def test_sign_with_full_card_succeeds(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100_signing_success.db")
    _admin_id, operator_id = seed_users(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)
    created = service.create_card(make_create_request(), actor_id=operator_id)

    signed = service.sign_card(
        created.id,
        Form100SignV2Request(signed_by="doctor"),
        actor_id=operator_id,
        expected_version=created.version,
    )

    assert signed.status == "SIGNED"
    assert signed.signed_version == signed.version


def test_existing_signed_cards_remain_exportable_without_revalidation(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100_legacy_signed_export.db")
    _admin_id, operator_id = seed_users(session_factory)
    card_id = "legacy-signed-card"
    now = datetime(2026, 5, 8, 9, 0, tzinfo=UTC).replace(tzinfo=None)
    with session_factory() as session:
        session.add(
            models.Form100V2(
                id=card_id,
                created_at=now,
                created_by="legacy",
                updated_at=now,
                updated_by="legacy",
                status="SIGNED",
                version=1,
                signed_version=1,
                is_archived=False,
                main_full_name="Legacy Signed",
                main_unit="Unit",
                main_diagnosis="Legacy diagnosis",
                signed_by="legacy doctor",
                signed_at=now,
            )
        )
        session.add(models.Form100DataV2(id="legacy-signed-data", form100_id=card_id))

    service = Form100ServiceV2(session_factory=session_factory)
    pdf_path = tmp_path / "legacy.pdf"

    result = service.export_pdf(card_id, pdf_path, actor_id=operator_id)

    assert pdf_path.exists()
    assert result["sha256"]
