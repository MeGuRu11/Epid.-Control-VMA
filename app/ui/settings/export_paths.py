"""UI-уровневый helper для использования настроенных пользователем папок экспорта.

Используется существующими view-классами (Form100, Analytics, Import/Export),
чтобы передавать в ``QFileDialog.getSaveFileName`` начальный путь, соответствующий
выбранной пользователем папке. Подход — минимально-инвазивный: вместо проброса
``UserPreferencesService`` в конструктор каждого view, мы регистрируем его один раз
при старте приложения, а view получают значение через простой вызов функции.

Если сервис не был зарегистрирован (например, в unit-тестах view) — функция
возвращает имя файла без префикса, что соответствует прежнему поведению.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from app.application.services.user_preferences_service import UserPreferencesService

logger = logging.getLogger(__name__)

ExportKind = Literal["pdf", "excel", "zip", "backup"]

_current_service: UserPreferencesService | None = None


def install_preferences_service(service: UserPreferencesService) -> None:
    """Зарегистрировать сервис настроек как источник дефолтных папок."""
    global _current_service
    _current_service = service


def reset_preferences_service() -> None:
    """Сбросить регистрацию (нужно в тестах)."""
    global _current_service
    _current_service = None


def get_export_dir(kind: ExportKind) -> str:
    """Получить путь к папке указанного типа из настроек, либо пустую строку."""
    service = _current_service
    if service is None:
        return ""
    prefs = service.current
    if kind == "pdf":
        return prefs.pdf_export_dir
    if kind == "excel":
        return prefs.excel_export_dir
    if kind == "zip":
        return prefs.zip_export_dir
    if kind == "backup":
        return prefs.backup_dir
    return ""


def compose_save_path(kind: ExportKind, filename: str) -> str:
    """Сформировать предложенный путь сохранения для ``QFileDialog``.

    Если папка задана и существует/может быть создана — возвращает
    ``<папка>/<filename>``. Если нет — возвращает только имя файла,
    как было до настроек (это сохраняет прежнее поведение приложения).
    """
    base_dir = get_export_dir(kind)
    if not base_dir:
        return filename
    try:
        base_path = Path(base_dir)
        base_path.mkdir(parents=True, exist_ok=True)
    except OSError:
        logger.exception("Failed to ensure export directory exists: %s", base_dir)
        return filename
    return str(base_path / filename)


def get_open_dir(kind: ExportKind) -> str:
    """Папка по умолчанию для ``QFileDialog.getOpenFileName`` (импорт)."""
    return get_export_dir(kind)
