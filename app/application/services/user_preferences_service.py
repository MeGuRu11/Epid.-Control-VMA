"""Сервис управления пользовательскими настройками.

Отвечает за:
- загрузку настроек при старте (с применением дефолтов и ENV-переопределений);
- сохранение изменений через ``PreferencesRepository``;
- уведомление подписчиков (UI) об изменениях для live-применения.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from pathlib import Path

from app.application.dto.user_preferences_dto import (
    UserPreferences,
    default_backup_dir,
    default_export_dir,
)
from app.config import DATA_DIR, Settings
from app.infrastructure.preferences.preferences_repository import PreferencesRepository

logger = logging.getLogger(__name__)

PreferencesObserver = Callable[[UserPreferences], None]


class UserPreferencesService:
    """Singleton-сервис настроек: текущее состояние в памяти + persistence."""

    def __init__(
        self,
        repository: PreferencesRepository,
        defaults_settings: Settings,
        data_dir: Path = DATA_DIR,
    ) -> None:
        self._repo = repository
        self._defaults_settings = defaults_settings
        self._data_dir = data_dir
        self._observers: list[PreferencesObserver] = []
        self._current = self._load_initial()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def current(self) -> UserPreferences:
        return self._current

    def reload(self) -> UserPreferences:
        """Перечитать настройки с диска (например, после внешнего сброса)."""
        self._current = self._load_initial()
        self._notify()
        return self._current

    def update(self, new_prefs: UserPreferences) -> UserPreferences:
        """Применить новые настройки: сохранить и оповестить подписчиков."""
        try:
            self._repo.save(new_prefs.to_dict())
        except OSError:
            logger.exception("Failed to persist user preferences")
            raise
        self._current = new_prefs
        self._notify()
        return self._current

    def reset_to_defaults(self) -> UserPreferences:
        """Сбросить все настройки к умолчаниям и удалить файл."""
        try:
            self._repo.delete()
        except OSError:
            logger.exception("Failed to delete preferences file during reset")
            raise
        self._current = self._build_defaults()
        self._notify()
        return self._current

    def update_window_geometry(self, geometry: tuple[int, int, int, int]) -> None:
        """Сохранить геометрию окна, не оповещая UI-подписчиков."""
        if not self._current.remember_window_geometry:
            return
        if self._current.last_window_geometry == geometry:
            return
        new_prefs = self._current.with_updates(last_window_geometry=geometry)
        try:
            self._repo.save(new_prefs.to_dict())
        except OSError:
            logger.exception("Failed to persist window geometry")
            return
        self._current = new_prefs

    def subscribe(self, observer: PreferencesObserver) -> Callable[[], None]:
        """Подписаться на изменения. Возвращает функцию-отписку."""
        self._observers.append(observer)

        def _unsubscribe() -> None:
            with contextlib.suppress(ValueError):
                self._observers.remove(observer)

        return _unsubscribe

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_defaults(self) -> UserPreferences:
        """Дефолты учитывают ENV-переопределения из ``Settings``."""
        return UserPreferences(
            ui_density=self._defaults_settings.ui_density,
            ui_animation_policy=self._defaults_settings.ui_animation_policy,
            ui_premium_enabled=self._defaults_settings.ui_premium_enabled,
            session_timeout_minutes=self._defaults_settings.session_timeout_minutes,
            pdf_export_dir=default_export_dir(self._data_dir, "pdf"),
            excel_export_dir=default_export_dir(self._data_dir, "excel"),
            zip_export_dir=default_export_dir(self._data_dir, "zip"),
            backup_dir=default_backup_dir(self._data_dir),
        )

    def _load_initial(self) -> UserPreferences:
        defaults = self._build_defaults()
        stored = self._repo.load()
        if stored is None:
            return defaults
        merged_data = {**defaults.to_dict(), **stored}
        return UserPreferences.from_dict(merged_data)

    def _notify(self) -> None:
        for observer in list(self._observers):
            try:
                observer(self._current)
            except Exception:  # noqa: BLE001
                logger.exception("User preferences observer raised an exception")
