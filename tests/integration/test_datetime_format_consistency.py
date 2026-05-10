from __future__ import annotations

import json
import zipfile
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from app.application.dto.form100_v2_dto import Form100SignV2Request
from app.application.services.exchange_service import ExchangeService
from app.application.services.form100_service_v2 import Form100ServiceV2
from tests.integration.test_exchange_service_import_reports import make_session_factory, seed_actor
from tests.integration.test_form100_v2_service import make_create_request


def _iter_datetime_fields(payload: Any, path: str = "$") -> Iterator[tuple[str, str]]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            next_path = f"{path}.{key}"
            if key.endswith("_at") and value is not None:
                assert isinstance(value, str), f"datetime field is not a string at {next_path}: {value!r}"
                yield next_path, value
            yield from _iter_datetime_fields(value, next_path)
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            yield from _iter_datetime_fields(item, f"{path}[{index}]")


def _assert_datetime_fields_are_iso_with_tz(payload: Any) -> None:
    checked = 0
    for path, value in _iter_datetime_fields(payload):
        parsed = datetime.fromisoformat(value)
        assert parsed.tzinfo is not None, f"naive datetime in {path}: {value!r}"
        checked += 1
    assert checked > 0


def test_all_datetime_fields_in_form100_export_are_iso_with_tz(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100_datetime_consistency.db")
    actor_id = seed_actor(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)
    created = service.create_card(make_create_request(), actor_id=actor_id)
    service.sign_card(
        created.id,
        Form100SignV2Request(signed_by="doctor"),
        actor_id=actor_id,
        expected_version=created.version,
    )

    zip_path = tmp_path / "form100_package.zip"
    service.export_package_zip(file_path=zip_path, actor_id=actor_id, card_id=created.id, exported_by="admin")

    with zipfile.ZipFile(zip_path, "r") as zf:
        payload = json.loads(zf.read("form100.json"))

    _assert_datetime_fields_are_iso_with_tz(payload)


def test_all_datetime_fields_in_full_export_are_iso_with_tz(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "full_export_datetime_consistency.db")
    actor_id = seed_actor(session_factory)
    form100_service = Form100ServiceV2(session_factory=session_factory)
    form100_service.create_card(make_create_request(), actor_id=actor_id)
    service = ExchangeService(session_factory=session_factory)
    json_path = tmp_path / "full_export.json"

    service.export_json(json_path, exported_by="exchange_admin", actor_id=actor_id)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    _assert_datetime_fields_are_iso_with_tz(payload)
