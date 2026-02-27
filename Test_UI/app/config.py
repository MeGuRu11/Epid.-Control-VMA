
from dataclasses import dataclass
from pathlib import Path
from platformdirs import user_data_dir

APP_NAME = "EpiSafe"
APP_AUTHOR = "EpiSafe"

@dataclass(frozen=True)
class AppDirs:
    base: Path
    data: Path
    db_path: Path

def get_app_dirs() -> AppDirs:
    base = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    data = base / "data"
    data.mkdir(parents=True, exist_ok=True)
    db_path = data / "app.db"
    return AppDirs(base=base, data=data, db_path=db_path)
