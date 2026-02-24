import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from platformdirs import user_data_dir

APP_NAME = "epid-control"
APP_AUTHOR = "epid-control"
LEGACY_APP_NAME = "codex-emr-lab"
LEGACY_APP_AUTHOR = "codex"

AnimationPolicy = Literal["adaptive", "full", "minimal"]
UiDensity = Literal["compact", "normal"]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_animation_policy(name: str, default: AnimationPolicy) -> AnimationPolicy:
    raw = (os.getenv(name) or "").strip().lower()
    if raw in {"adaptive", "full", "minimal"}:
        return cast(AnimationPolicy, raw)
    return default


def _env_ui_density(name: str, default: UiDensity) -> UiDensity:
    raw = (os.getenv(name) or "").strip().lower()
    if raw in {"compact", "normal"}:
        return cast(UiDensity, raw)
    return default

def _resolve_data_dir() -> Path:
    env_dir = os.getenv("EPIDCONTROL_DATA_DIR") or os.getenv("CODEX_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    new_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    legacy_dir = Path(user_data_dir(LEGACY_APP_NAME, LEGACY_APP_AUTHOR))
    if legacy_dir.exists() and not new_dir.exists():
        try:
            new_dir.mkdir(parents=True, exist_ok=True)
            legacy_db = legacy_dir / "app.db"
            new_db = new_dir / "app.db"
            if legacy_db.exists() and not new_db.exists():
                new_db.write_bytes(legacy_db.read_bytes())
            legacy_logs = legacy_dir / "logs"
            if legacy_logs.exists():
                new_logs = new_dir / "logs"
                new_logs.mkdir(parents=True, exist_ok=True)
                for file in legacy_logs.glob("*"):
                    if file.is_file():
                        target = new_logs / file.name
                        if not target.exists():
                            target.write_bytes(file.read_bytes())
        except Exception:
            return legacy_dir
    return new_dir


DATA_DIR = _resolve_data_dir()
LOG_DIR = DATA_DIR / "logs"
DB_FILE = Path(os.getenv("EPIDCONTROL_DB_FILE") or os.getenv("CODEX_DB_FILE") or (DATA_DIR / "app.db"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE.parent.mkdir(parents=True, exist_ok=True)


def default_database_url() -> str:
    # SQLite URL uses forward slashes; as_posix() keeps it cross-platform.
    return f"sqlite:///{DB_FILE.as_posix()}"


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", default_database_url())
    echo_sql: bool = os.getenv("SQL_ECHO", "0") == "1"
    ui_premium_enabled: bool = _env_bool("EPIDCONTROL_UI_PREMIUM", True)
    ui_animation_policy: AnimationPolicy = _env_animation_policy("EPIDCONTROL_UI_ANIMATION", "adaptive")
    ui_density: UiDensity = _env_ui_density("EPIDCONTROL_UI_DENSITY", "normal")
    form100_v2_enabled: bool = _env_bool("EPIDCONTROL_FORM100_V2_ENABLED", True)


settings = Settings()
