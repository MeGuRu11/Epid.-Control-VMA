from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from app.application.services.exchange_service import ExchangeService


def _write_zip(zip_path: Path, entries: dict[str, str]) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)


def test_import_zip_rejects_unsafe_archive_path(tmp_path: Path) -> None:
    service = ExchangeService()
    archive_path = tmp_path / "unsafe.zip"
    _write_zip(archive_path, {"../evil.txt": "bad"})

    with pytest.raises(ValueError) as exc_info:
        service.import_zip(archive_path)

    message = str(exc_info.value)
    assert "ZIP" in message
    assert "evil.txt" in message


def test_import_zip_reports_missing_manifest(tmp_path: Path) -> None:
    service = ExchangeService()
    archive_path = tmp_path / "no_manifest.zip"
    _write_zip(archive_path, {"export.xlsx": "placeholder"})

    with pytest.raises(ValueError) as exc_info:
        service.import_zip(archive_path)

    assert "manifest.json" in str(exc_info.value)


def test_import_zip_reports_missing_file_from_manifest(tmp_path: Path) -> None:
    service = ExchangeService()
    archive_path = tmp_path / "missing_payload.zip"
    manifest = {
        "schema_version": "1.0",
        "files": [{"name": "export.xlsx", "sha256": "deadbeef"}],
    }
    _write_zip(archive_path, {"manifest.json": json.dumps(manifest, ensure_ascii=False)})

    with pytest.raises(ValueError) as exc_info:
        service.import_zip(archive_path)

    assert "export.xlsx" in str(exc_info.value)
