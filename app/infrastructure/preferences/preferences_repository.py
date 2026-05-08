"""JSON-based persistent storage for user preferences.

Стратегия хранения:
- Файл ``preferences.json`` в каталоге данных приложения (``DATA_DIR``).
- Запись атомарная (через временный файл + ``Path.replace``), чтобы не оставлять
  частично записанные файлы при сбое.
- Если файл повреждён или содержит несовместимую схему — возвращаем ``None`` и
  пишем предупреждение в лог. Сервис в этом случае использует значения по умолчанию.
- Хранится только сериализуемое представление (dict) — само DTO собирает сервис.
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PREFERENCES_FILE_NAME = "preferences.json"
PREFERENCES_SCHEMA_VERSION = 1


class PreferencesRepository:
    """Атомарный JSON-репозиторий пользовательских настроек."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._file_path = data_dir / PREFERENCES_FILE_NAME

    @property
    def file_path(self) -> Path:
        return self._file_path

    def load(self) -> dict[str, Any] | None:
        """Прочитать настройки из файла. None — если файла нет или он повреждён."""
        if not self._file_path.exists():
            return None
        try:
            with self._file_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed to read preferences file: %s", self._file_path)
            return None
        if not isinstance(payload, dict):
            logger.warning("Preferences file has unexpected structure: %s", self._file_path)
            return None
        version = payload.get("schema_version")
        if version != PREFERENCES_SCHEMA_VERSION:
            logger.info(
                "Preferences schema version mismatch (file=%s, expected=%s). Ignoring file.",
                version,
                PREFERENCES_SCHEMA_VERSION,
            )
            return None
        values = payload.get("values")
        if not isinstance(values, dict):
            return None
        return dict(values)

    def save(self, values: dict[str, Any]) -> None:
        """Записать настройки атомарно. Создаёт каталог, если его ещё нет."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": PREFERENCES_SCHEMA_VERSION,
            "values": values,
        }
        # tempfile в том же каталоге → Path.replace атомарно на одном FS.
        fd, tmp_name = tempfile.mkstemp(
            prefix=".preferences-", suffix=".tmp", dir=str(self._data_dir)
        )
        tmp_path = Path(tmp_name)
        try:
            with open(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            tmp_path.replace(self._file_path)
        except OSError:
            logger.exception("Failed to save preferences file: %s", self._file_path)
            tmp_path.unlink(missing_ok=True)
            raise

    def delete(self) -> None:
        """Удалить файл настроек (используется при сбросе к умолчаниям)."""
        try:
            self._file_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Failed to delete preferences file: %s", self._file_path)
            raise
