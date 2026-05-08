from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from app.application.dto.form100_v2_dto import Form100SignV2Request
from app.application.services.form100_service_v2 import Form100ServiceV2
from tests.integration.test_form100_v2_service import (
    make_create_request,
    make_session_factory,
    seed_users,
)


def test_zip_pdf_sha256_matches_manifest_and_form100_json(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100_zip_integrity.db")
    admin_id, operator_id = seed_users(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)
    created = service.create_card(make_create_request(), actor_id=operator_id)
    service.sign_card(
        created.id,
        Form100SignV2Request(signed_by="doctor"),
        actor_id=operator_id,
        expected_version=created.version,
    )

    zip_path = tmp_path / "form100_package.zip"
    service.export_package_zip(file_path=zip_path, actor_id=admin_id, card_id=created.id, exported_by="admin")

    pdf_name = f"form100/{created.id}.pdf"
    with zipfile.ZipFile(zip_path, "r") as zf:
        manifest = json.loads(zf.read("manifest.json"))
        form100_json = json.loads(zf.read("form100.json"))
        pdf_bytes = zf.read(pdf_name)

    actual_sha = hashlib.sha256(pdf_bytes).hexdigest()
    manifest_pdf = next(item for item in manifest["files"] if item["name"] == pdf_name)
    exported_card = form100_json["cards"][0]

    assert manifest_pdf["sha256"] == actual_sha
    assert exported_card["artifact_sha256"] == actual_sha
    assert exported_card["artifact_path"] == pdf_name
