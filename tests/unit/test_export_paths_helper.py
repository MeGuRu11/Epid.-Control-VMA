from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from app.application.services.user_preferences_service import UserPreferencesService
from app.config import Settings
from app.infrastructure.preferences.preferences_repository import PreferencesRepository
from app.ui.settings.export_paths import (
    compose_save_path,
    get_export_dir,
    get_open_dir,
    install_preferences_service,
    reset_preferences_service,
)


@pytest.fixture(autouse=True)
def _reset_module() -> Generator[None, None, None]:
    # Каждому тесту — чистое глобальное состояние модуля.
    reset_preferences_service()
    yield
    reset_preferences_service()


def _make_service(tmp_path: Path) -> UserPreferencesService:
    return UserPreferencesService(
        repository=PreferencesRepository(tmp_path),
        defaults_settings=Settings(),
        data_dir=tmp_path,
    )


def test_compose_save_path_returns_filename_when_service_not_installed() -> None:
    assert compose_save_path("pdf", "report.pdf") == "report.pdf"


def test_get_export_dir_empty_when_service_not_installed() -> None:
    assert get_export_dir("pdf") == ""
    assert get_open_dir("zip") == ""


def test_compose_save_path_uses_pdf_dir_when_service_installed(tmp_path: Path) -> None:
    custom = tmp_path / "my_pdfs"
    service = _make_service(tmp_path)
    service.update(service.current.with_updates(pdf_export_dir=str(custom)))
    install_preferences_service(service)

    result = compose_save_path("pdf", "report.pdf")

    assert result == str(custom / "report.pdf")
    assert custom.is_dir(), "Папка должна быть создана автоматически"


def test_compose_save_path_returns_filename_only_when_dir_is_empty(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    service.update(service.current.with_updates(pdf_export_dir=""))
    install_preferences_service(service)

    assert compose_save_path("pdf", "x.pdf") == "x.pdf"


def test_get_export_dir_returns_correct_per_kind(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    service.update(
        service.current.with_updates(
            pdf_export_dir="/p", excel_export_dir="/e", zip_export_dir="/z", backup_dir="/b"
        )
    )
    install_preferences_service(service)

    assert get_export_dir("pdf") == "/p"
    assert get_export_dir("excel") == "/e"
    assert get_export_dir("zip") == "/z"
    assert get_export_dir("backup") == "/b"


def test_reset_preferences_service_unbinds_state(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    service.update(service.current.with_updates(pdf_export_dir=str(tmp_path)))
    install_preferences_service(service)
    assert get_export_dir("pdf") == str(tmp_path)

    reset_preferences_service()
    assert get_export_dir("pdf") == ""
    assert compose_save_path("pdf", "x.pdf") == "x.pdf"
