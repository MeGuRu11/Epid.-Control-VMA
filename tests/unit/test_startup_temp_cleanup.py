"""Tests for cleanup_stale_temp_dirs in app.bootstrap.startup."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.bootstrap.startup import cleanup_stale_temp_dirs


@pytest.fixture()
def tmp_run_dir(tmp_path: Path) -> Path:
    run_dir = tmp_path / "tmp_run"
    run_dir.mkdir()
    return run_dir


def test_removes_epid_temp_dirs(tmp_run_dir: Path) -> None:
    stale = tmp_run_dir / "epid-temp-abc123"
    stale.mkdir()
    (stale / "data.json").write_text("{}", encoding="utf-8")

    with patch("app.bootstrap.startup.Path.cwd", return_value=tmp_run_dir.parent):
        cleanup_stale_temp_dirs()

    assert not stale.exists()


def test_removes_form100_temp_dirs(tmp_run_dir: Path) -> None:
    stale = tmp_run_dir / "form100-v2-xyz789"
    stale.mkdir()

    with patch("app.bootstrap.startup.Path.cwd", return_value=tmp_run_dir.parent):
        cleanup_stale_temp_dirs()

    assert not stale.exists()


def test_preserves_non_matching_dirs(tmp_run_dir: Path) -> None:
    safe = tmp_run_dir / "epid-data"
    safe.mkdir()
    safe2 = tmp_run_dir / "some-other-dir"
    safe2.mkdir()

    with patch("app.bootstrap.startup.Path.cwd", return_value=tmp_run_dir.parent):
        cleanup_stale_temp_dirs()

    assert safe.exists()
    assert safe2.exists()


def test_noop_when_no_tmp_run(tmp_path: Path) -> None:
    # tmp_run doesn't exist — should not raise
    with patch("app.bootstrap.startup.Path.cwd", return_value=tmp_path):
        cleanup_stale_temp_dirs()


def test_mixed_cleanup(tmp_run_dir: Path) -> None:
    stale1 = tmp_run_dir / "epid-temp-111"
    stale1.mkdir()
    stale2 = tmp_run_dir / "form100-v2-222"
    stale2.mkdir()
    safe = tmp_run_dir / "reports"
    safe.mkdir()

    with patch("app.bootstrap.startup.Path.cwd", return_value=tmp_run_dir.parent):
        cleanup_stale_temp_dirs()

    assert not stale1.exists()
    assert not stale2.exists()
    assert safe.exists()
