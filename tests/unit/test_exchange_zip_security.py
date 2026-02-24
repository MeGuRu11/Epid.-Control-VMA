from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from app.application.services.exchange_service import _safe_extract_zip


def _make_zip(zip_path: Path, files: dict[str, str]) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)


def test_safe_extract_zip_allows_regular_paths(tmp_path: Path) -> None:
    archive = tmp_path / "ok.zip"
    out_dir = tmp_path / "out"
    _make_zip(archive, {"manifest.json": "{}", "data/export.xlsx": "xlsx"})

    with zipfile.ZipFile(archive, "r") as zf:
        extracted = _safe_extract_zip(zf, out_dir)

    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "data" / "export.xlsx").exists()
    assert len(extracted) == 2


@pytest.mark.parametrize(
    "member_name",
    [
        "../evil.txt",
        "..\\evil.txt",
        "/abs/evil.txt",
        "\\abs\\evil.txt",
        "C:/evil.txt",
    ],
)
def test_safe_extract_zip_rejects_traversal_and_absolute_paths(tmp_path: Path, member_name: str) -> None:
    archive = tmp_path / "bad.zip"
    out_dir = tmp_path / "out"
    _make_zip(archive, {member_name: "bad"})

    with zipfile.ZipFile(archive, "r") as zf, pytest.raises(ValueError) as exc_info:
        _safe_extract_zip(zf, out_dir)

    message = str(exc_info.value)
    assert "evil.txt" in message or "abs" in message
