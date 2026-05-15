"""DTO пользовательских настроек.

Frozen dataclass — единый источник правды о форме и типах настроек.
Сериализуется в plain-dict (для JSON-репозитория) и обратно.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any, Literal, cast

AnimationPolicy = Literal["adaptive", "full", "minimal"]
UiDensity = Literal["compact", "normal"]
WindowInitialState = Literal["normal", "maximized", "last"]
BackupFrequency = Literal["startup_daily", "startup_only", "manual"]

_ANIMATION_VALUES: tuple[AnimationPolicy, ...] = ("adaptive", "full", "minimal")
_DENSITY_VALUES: tuple[UiDensity, ...] = ("compact", "normal")
_WINDOW_STATE_VALUES: tuple[WindowInitialState, ...] = ("normal", "maximized", "last")
_BACKUP_FREQ_VALUES: tuple[BackupFrequency, ...] = (
    "startup_daily",
    "startup_only",
    "manual",
)

SESSION_TIMEOUT_MIN = 5
SESSION_TIMEOUT_MAX = 240
BACKUP_RETENTION_MIN = 1
BACKUP_RETENTION_MAX = 50


@dataclass(frozen=True)
class UserPreferences:
    """Снимок всех пользовательских настроек."""

    # --- Внешний вид ---
    ui_density: UiDensity = "normal"
    ui_animation_policy: AnimationPolicy = "adaptive"
    ui_premium_enabled: bool = True
    ui_background_enabled: bool = True

    # --- Окно ---
    remember_window_geometry: bool = True
    window_initial_state: WindowInitialState = "last"
    last_window_geometry: tuple[int, int, int, int] | None = None  # (x, y, w, h)

    # --- Папки экспорта/импорта ---
    pdf_export_dir: str = ""
    excel_export_dir: str = ""
    zip_export_dir: str = ""
    backup_dir: str = ""
    last_import_dir: str = ""

    # --- Безопасность ---
    session_timeout_minutes: int = 30
    auto_logout_enabled: bool = True
    confirm_before_exit: bool = True

    # --- Резервные копии ---
    auto_backup_enabled: bool = True
    auto_backup_frequency: BackupFrequency = "startup_daily"
    backup_retention_count: int = 10

    # --- Уведомления ---
    toasts_enabled: bool = True
    sound_enabled: bool = False

    # --- Экспериментальные функции ---
    use_analytics_v2: bool = False

    # ------------------------------------------------------------------
    # сериализация / десериализация
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # tuple → list для JSON
        if data["last_window_geometry"] is not None:
            data["last_window_geometry"] = list(data["last_window_geometry"])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserPreferences:
        """Собрать DTO из dict, подставляя дефолты для отсутствующих/невалидных полей."""
        defaults = cls()
        kwargs: dict[str, Any] = {}
        for field in fields(cls):
            raw = data.get(field.name, getattr(defaults, field.name))
            kwargs[field.name] = _coerce_field_value(field.name, raw, getattr(defaults, field.name))
        return cls(**kwargs)

    def with_updates(self, **changes: Any) -> UserPreferences:
        """Вернуть новый DTO с применёнными изменениями (валидация делается тут же)."""
        merged = replace(self, **changes)
        # пересобираем через from_dict, чтобы привести к допустимым значениям
        return UserPreferences.from_dict(merged.to_dict())


# ----------------------------------------------------------------------
# Внутренние помощники валидации/приведения
# ----------------------------------------------------------------------


def _coerce_field_value(name: str, raw: Any, default: Any) -> Any:
    if name == "ui_density":
        return raw if raw in _DENSITY_VALUES else default
    if name == "ui_animation_policy":
        return raw if raw in _ANIMATION_VALUES else default
    if name == "window_initial_state":
        return raw if raw in _WINDOW_STATE_VALUES else default
    if name == "auto_backup_frequency":
        return raw if raw in _BACKUP_FREQ_VALUES else default
    if name == "session_timeout_minutes":
        return _clamp_int(raw, default, SESSION_TIMEOUT_MIN, SESSION_TIMEOUT_MAX)
    if name == "backup_retention_count":
        return _clamp_int(raw, default, BACKUP_RETENTION_MIN, BACKUP_RETENTION_MAX)
    if name == "last_window_geometry":
        return _coerce_geometry(raw)
    if isinstance(default, bool):
        return bool(raw) if isinstance(raw, bool) else default
    if isinstance(default, str):
        return raw if isinstance(raw, str) else default
    return raw


def _clamp_int(raw: Any, default: int, lo: int, hi: int) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return default
    else:
        value = raw
    return max(lo, min(hi, value))


def _coerce_geometry(raw: Any) -> tuple[int, int, int, int] | None:
    if raw is None:
        return None
    if not isinstance(raw, list | tuple) or len(raw) != 4:
        return None
    try:
        values = tuple(int(v) for v in raw)
    except (TypeError, ValueError):
        return None
    return cast(tuple[int, int, int, int], values)


def default_export_dir(data_dir: Path, sub: str) -> str:
    """Дефолтный путь для экспортов: <DATA_DIR>/exports/<sub>."""
    return str((data_dir / "exports" / sub).resolve())


def default_backup_dir(data_dir: Path) -> str:
    """Дефолтный путь для резервных копий: <DATA_DIR>/backups."""
    return str((data_dir / "backups").resolve())
