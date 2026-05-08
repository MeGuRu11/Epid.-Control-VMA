from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialogButtonBox, QSpinBox

from app.application.services.user_preferences_service import UserPreferencesService
from app.config import Settings
from app.infrastructure.preferences.preferences_repository import PreferencesRepository
from app.ui.settings.settings_dialog import SettingsDialog


def _make_service(tmp_path: Path) -> UserPreferencesService:
    return UserPreferencesService(
        repository=PreferencesRepository(tmp_path),
        defaults_settings=Settings(),
        data_dir=tmp_path,
    )


def test_settings_dialog_builds_with_defaults(qapp, tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    dialog = SettingsDialog(preferences_service=service)
    try:
        dialog.show()
        qapp.processEvents()

        # Проверяем, что вкладок ровно семь и все они отображают видимые надписи.
        assert dialog._tabs.count() == 7
        labels = [dialog._tabs.tabText(i) for i in range(dialog._tabs.count())]
        assert labels == [
            "Внешний вид",
            "Окно",
            "Папки",
            "Безопасность",
            "Резервные копии",
            "Уведомления",
            "О программе",
        ]

        # Дефолтные значения формы соответствуют DTO.
        assert dialog._density_combo.currentData() == service.current.ui_density
        assert dialog._session_timeout_spin.value() == service.current.session_timeout_minutes
        assert dialog._auto_logout_check.isChecked() is service.current.auto_logout_enabled
    finally:
        dialog.close()


def test_settings_dialog_session_timeout_disabled_when_auto_logout_off(qapp, tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    service.update(service.current.with_updates(auto_logout_enabled=False))

    dialog = SettingsDialog(preferences_service=service)
    try:
        dialog.show()
        qapp.processEvents()
        assert dialog._auto_logout_check.isChecked() is False
        assert dialog._session_timeout_spin.isEnabled() is False
    finally:
        dialog.close()


def test_settings_dialog_apply_persists_changes(qapp, tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    dialog = SettingsDialog(preferences_service=service)
    try:
        dialog.show()
        qapp.processEvents()

        # Меняем плотность и таймаут.
        compact_index = dialog._density_combo.findData("compact")
        dialog._density_combo.setCurrentIndex(compact_index)
        dialog._session_timeout_spin.setValue(75)

        dialog._on_apply_clicked()
        qapp.processEvents()

        assert service.current.ui_density == "compact"
        assert service.current.session_timeout_minutes == 75

        # Файл реально записан и содержит новые значения.
        fresh = _make_service(tmp_path)
        assert fresh.current.ui_density == "compact"
        assert fresh.current.session_timeout_minutes == 75
    finally:
        dialog.close()


def test_settings_dialog_save_closes_dialog(qapp, tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    dialog = SettingsDialog(preferences_service=service)
    try:
        dialog.show()
        qapp.processEvents()

        save_btn = dialog._button_box.button(QDialogButtonBox.StandardButton.Save)
        assert save_btn is not None
        save_btn.click()
        qapp.processEvents()

        assert not dialog.isVisible()
    finally:
        dialog.close()


def test_settings_dialog_cancel_does_not_persist(qapp, tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    initial_density = service.current.ui_density

    dialog = SettingsDialog(preferences_service=service)
    try:
        dialog.show()
        qapp.processEvents()

        dialog._density_combo.setCurrentIndex(dialog._density_combo.findData("compact"))
        cancel_btn = dialog._button_box.button(QDialogButtonBox.StandardButton.Cancel)
        assert cancel_btn is not None
        cancel_btn.click()
        qapp.processEvents()
    finally:
        dialog.close()

    assert service.current.ui_density == initial_density


def test_settings_dialog_reset_geometry_button_clears_saved_geometry(
    qapp, tmp_path: Path, monkeypatch
) -> None:
    service = _make_service(tmp_path)
    service.update_window_geometry((1, 2, 800, 600))
    assert service.current.last_window_geometry == (1, 2, 800, 600)

    # Мокаем модальный QMessageBox: в headless среде он блокирует поток.
    from app.ui.settings import settings_dialog as settings_module

    monkeypatch.setattr(settings_module, "exec_message_box", lambda *a, **kw: None)

    dialog = SettingsDialog(preferences_service=service)
    try:
        dialog.show()
        qapp.processEvents()

        # Нажимаем «Сбросить геометрию», затем «Применить».
        dialog._reset_geometry_btn.click()
        qapp.processEvents()
        dialog._on_apply_clicked()
        qapp.processEvents()
    finally:
        dialog.close()

    assert service.current.last_window_geometry is None


def test_settings_dialog_session_timeout_spin_has_correct_range(qapp, tmp_path: Path) -> None:
    from app.application.dto.user_preferences_dto import (
        SESSION_TIMEOUT_MAX,
        SESSION_TIMEOUT_MIN,
    )

    service = _make_service(tmp_path)
    dialog = SettingsDialog(preferences_service=service)
    try:
        dialog.show()
        qapp.processEvents()
        spin = dialog._session_timeout_spin
        assert isinstance(spin, QSpinBox)
        assert spin.minimum() == SESSION_TIMEOUT_MIN
        assert spin.maximum() == SESSION_TIMEOUT_MAX
    finally:
        dialog.close()


def test_settings_dialog_folder_pickers_show_default_paths(qapp, tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    dialog = SettingsDialog(preferences_service=service)
    try:
        dialog.show()
        qapp.processEvents()
        assert dialog._pdf_dir_picker.value == service.current.pdf_export_dir
        assert dialog._excel_dir_picker.value == service.current.excel_export_dir
        assert dialog._zip_dir_picker.value == service.current.zip_export_dir
        assert dialog._backup_dir_picker.value == service.current.backup_dir
    finally:
        dialog.close()
