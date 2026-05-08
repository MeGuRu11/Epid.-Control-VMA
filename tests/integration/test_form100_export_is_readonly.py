from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from app.application.dto.form100_v2_dto import Form100SignV2Request
from app.application.services.form100_service_v2 import Form100ServiceV2
from app.infrastructure.db import models_sqlalchemy as models
from tests.integration.test_form100_v2_service import (
    make_create_request,
    make_session_factory,
    seed_users,
)


def _snapshot_card(row: models.Form100V2) -> dict[str, Any]:
    return {
        "status": row.status,
        "version": row.version,
        "signed_version": row.signed_version,
        "updated_at": row.updated_at,
        "updated_by": row.updated_by,
        "artifact_path": row.artifact_path,
        "artifact_sha256": row.artifact_sha256,
    }


def test_sign_card_sets_signed_version_to_signed_card_version(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100_signed_version.db")
    _admin_id, operator_id = seed_users(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)

    created = service.create_card(make_create_request(), actor_id=operator_id)
    signed = service.sign_card(
        created.id,
        Form100SignV2Request(signed_by="doctor"),
        actor_id=operator_id,
        expected_version=created.version,
    )

    assert signed.version == 2
    assert signed.signed_version == signed.version
    with session_factory() as session:
        row = session.get(models.Form100V2, created.id)
        assert row is not None
        assert row.signed_version == signed.version
        assert row.artifact_path is None
        assert row.artifact_sha256 is None


def test_export_pdf_is_readonly_and_records_each_generation(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100_pdf_readonly.db")
    _admin_id, operator_id = seed_users(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)
    created = service.create_card(make_create_request(), actor_id=operator_id)
    signed = service.sign_card(
        created.id,
        Form100SignV2Request(signed_by="doctor"),
        actor_id=operator_id,
        expected_version=created.version,
    )

    with session_factory() as session:
        before_row = session.get(models.Form100V2, created.id)
        assert before_row is not None
        before = _snapshot_card(before_row)

    first_pdf = tmp_path / "first.pdf"
    second_pdf = tmp_path / "second.pdf"
    first_result = service.export_pdf(created.id, first_pdf, actor_id=operator_id)
    second_result = service.export_pdf(created.id, second_pdf, actor_id=operator_id)

    with session_factory() as session:
        after_row = session.get(models.Form100V2, created.id)
        assert after_row is not None
        after = _snapshot_card(after_row)
        artifacts = (
            session.query(models.Form100Artifact)
            .filter(models.Form100Artifact.form100_id == created.id)
            .order_by(models.Form100Artifact.generated_at.asc())
            .all()
        )

    assert after == before
    assert after["version"] == signed.version
    assert len(artifacts) == 2
    assert [artifact.kind for artifact in artifacts] == ["pdf", "pdf"]
    assert [artifact.version_at_generation for artifact in artifacts] == [signed.version, signed.version]
    assert {artifact.sha256 for artifact in artifacts} == {
        cast(str, first_result["sha256"]),
        cast(str, second_result["sha256"]),
    }
    assert {Path(str(artifact.path)).name for artifact in artifacts} == {"first.pdf", "second.pdf"}


def test_zip_package_does_not_increment_form100_version(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100_zip_readonly.db")
    admin_id, operator_id = seed_users(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)
    created = service.create_card(make_create_request(), actor_id=operator_id)
    signed = service.sign_card(
        created.id,
        Form100SignV2Request(signed_by="doctor"),
        actor_id=operator_id,
        expected_version=created.version,
    )

    zip_path = tmp_path / "form100.zip"
    service.export_package_zip(file_path=zip_path, actor_id=admin_id, card_id=created.id, exported_by="admin")

    with session_factory() as session:
        row = session.get(models.Form100V2, created.id)
        assert row is not None
        assert row.version == signed.version
        assert row.signed_version == signed.version
