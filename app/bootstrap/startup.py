from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from PySide6.QtWidgets import QMessageBox
from sqlalchemy import inspect, select

from app.infrastructure.db.engine import get_engine
from app.infrastructure.db.fts_manager import FtsManager
from app.infrastructure.db.models_sqlalchemy import User


def check_startup_prerequisites(root_dir: Path, db_file: Path) -> bool:
    if not (root_dir / "alembic.ini").exists():
        QMessageBox.critical(
            None,
            "Ошибка",
            "Отсутствует alembic.ini. Проверьте установку приложения.",
        )
        return False
    migrations_dir = root_dir / "app" / "infrastructure" / "db" / "migrations"
    if not migrations_dir.exists():
        QMessageBox.critical(
            None,
            "Ошибка",
            "Отсутствует каталог миграций. Проверьте установку приложения.",
        )
        return False
    try:
        test_file = db_file.parent / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
    except Exception:
        QMessageBox.critical(
            None,
            "Ошибка",
            f"Нет прав на запись в каталог БД: {db_file.parent}",
        )
        return False
    return True


def run_migrations(root_dir: Path, database_url: str, log_dir: Path, db_file: Path) -> bool:
    try:
        cfg = Config(str(root_dir / "alembic.ini"))
        cfg.set_main_option(
            "script_location",
            str(root_dir / "app" / "infrastructure" / "db" / "migrations"),
        )
        cfg.set_main_option("sqlalchemy.url", database_url)
        try:
            command.upgrade(cfg, "head")
            return True
        except Exception as exc:  # noqa: BLE001
            if "MultipleHeads" in str(type(exc)) or "Multiple head" in str(exc):
                try:
                    command.upgrade(cfg, "heads")
                    return True
                except Exception:  # noqa: BLE001
                    logging.getLogger(__name__).exception("Failed to upgrade multiple heads")
                    raise
            raise
    except Exception:  # noqa: BLE001
        logger = logging.getLogger(__name__)
        logger.exception("Failed to run migrations")
        try:
            import traceback

            error_path = log_dir / "migration_error.log"
            error_path.parent.mkdir(parents=True, exist_ok=True)
            with error_path.open("a", encoding="utf-8") as handle:
                handle.write("\n--- Migration error ---\n")
                handle.write(f"DB: {db_file}\n")
                handle.write(f"Migrations: {root_dir / 'app' / 'infrastructure' / 'db' / 'migrations'}\n")
                handle.write(traceback.format_exc())
        except Exception:  # noqa: BLE001
            logger.exception("Failed to write migration error log")
        QMessageBox.critical(
            None,
            "Ошибка",
            "Не удалось применить миграции базы данных.\n"
            f"Подробности: {log_dir / 'migration_error.log'}",
        )
        return False


def ensure_schema_compatibility(
    root_dir: Path,
    database_url: str,
    log_dir: Path,
    db_file: Path,
) -> bool:
    try:
        engine = get_engine()
        inspector = inspect(engine)
        if "patients" not in inspector.get_table_names():
            return True
        columns = {col["name"] for col in inspector.get_columns("patients")}
        required = {"category", "military_unit", "military_district"}
        missing = required - columns
        if not missing:
            return True
        logging.getLogger(__name__).warning(
            "DB schema mismatch in 'patients' table. Missing columns: %s. DB path: %s",
            ", ".join(sorted(missing)),
            db_file,
        )
        if not run_migrations(root_dir, database_url, log_dir, db_file):
            return False
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("patients")}
        if required - columns:
            QMessageBox.critical(
                None,
                "Ошибка",
                "База данных устарела и не может быть обновлена автоматически.",
            )
            return False
        return True
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception("Failed to verify database schema")
        QMessageBox.critical(
            None,
            "Ошибка",
            f"Не удалось проверить структуру базы данных: {exc}",
        )
        return False


def ensure_fts_objects(session_factory) -> bool:
    fts_manager = FtsManager(session_factory=session_factory)
    if fts_manager.ensure_all():
        return True
    QMessageBox.critical(
        None,
        "Ошибка",
        "Не удалось инициализировать FTS-поиск.",
    )
    return False


def has_users(session_factory) -> bool:
    try:
        with session_factory() as session:
            return session.execute(select(User.id).limit(1)).first() is not None
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception("Failed to check users")
        return False


def initialize_database(
    *,
    root_dir: Path,
    db_file: Path,
    database_url: str,
    log_dir: Path,
    session_factory,
) -> bool:
    if not check_startup_prerequisites(root_dir, db_file):
        return False
    if not run_migrations(root_dir, database_url, log_dir, db_file):
        return False
    if not ensure_schema_compatibility(root_dir, database_url, log_dir, db_file):
        return False
    return ensure_fts_objects(session_factory)


def seed_core_data(container: Any) -> None:
    try:
        container.reference_service.seed_defaults()
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception("Failed to seed reference defaults")
    try:
        container.backup_service.ensure_daily_backup()
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception("Failed to run automatic backup")


def warn_missing_plot_dependencies() -> None:
    missing = []
    try:
        import pyqtgraph  # noqa: F401
    except Exception:
        missing.append("pyqtgraph")
    try:
        import matplotlib  # noqa: F401
    except Exception:
        missing.append("matplotlib")
    if missing:
        QMessageBox.warning(
            None,
            "Библиотеки не найдены",
            "Не установлены библиотеки для графиков: " + ", ".join(missing),
        )
